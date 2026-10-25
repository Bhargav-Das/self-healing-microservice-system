
import logging
import os
import subprocess
import sys
import time

from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv
from sqlalchemy import select, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

# -----------------------------------------
# STEP 1: Locate the project root
# -----------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(PROJECT_ROOT))

# -----------------------------------------
# STEP 2: Load .env BEFORE database imports
# -----------------------------------------

load_dotenv(
    dotenv_path=PROJECT_ROOT / ".env",
    override=True
)

# -----------------------------------------
# STEP 3: Configure local database hostname
# -----------------------------------------

os.environ["POSTGRES_HOST"] = "localhost"

# -----------------------------------------
# STEP 4: Import database models
# -----------------------------------------

from database.models import (
    FailureEvent,
    RecoveryEvent,
    Service,
)

# Load local PostgreSQL credentials
load_dotenv(PROJECT_ROOT / ".env", override=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("recovery-controller")

# Only these services may be recovered
ALLOWED_SERVICES = {
    "order-service": {
        "container": "order-service",
        "port": 8001,
    },
    "inventory-service": {
        "container": "inventory-service",
        "port": 8002,
    },
    "notification-service": {
        "container": "notification-service",
        "port": 8003,
    },
}

POLL_INTERVAL = 2
MAX_ATTEMPTS = 3
VERIFY_TIMEOUT = 30
COOLDOWN_SECONDS = 30

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    host="localhost",
    port=5432,
    database=os.environ["POSTGRES_DB"],
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

SessionLocal = sessionmaker(
    bind=engine,
    expire_on_commit=False,
)

# Local controller state
last_attempt = {}


def utc_now():
    return datetime.now(timezone.utc)


def find_pending_failures():
    """
    Return open failures that have not already
    reached the recovery attempt limit.
    """

    with SessionLocal() as db:
        failures = db.scalars(
            select(FailureEvent)
            .where(FailureEvent.status == "OPEN")
            .order_by(FailureEvent.id)
        ).all()

        pending = []

        for failure in failures:
            service = db.get(Service, failure.service_id)

            if service is None:
                continue

            if service.name not in ALLOWED_SERVICES:
                continue

            attempts = db.scalars(
                select(RecoveryEvent).where(
                    RecoveryEvent.failure_id == failure.id
                )
            ).all()

            if len(attempts) >= MAX_ATTEMPTS:
                continue

            pending.append({
                "failure_id": failure.id,
                "service_name": service.name,
                "attempt_number": len(attempts) + 1,
            })

        return pending


def start_container(container_name):
    """
    Start a stopped, allowlisted Docker container.
    """

    logger.info(
        "RECOVERY_ACTION container=%s action=start",
        container_name,
    )

    result = subprocess.run(
        ["docker", "start", container_name],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "Docker start failed"
        )


def verify_recovery(service_name, port):
    """
    Wait for the service to pass its health check.
    """

    url = f"http://127.0.0.1:{port}/health"
    deadline = time.monotonic() + VERIFY_TIMEOUT

    with httpx.Client(timeout=2.0) as client:
        while time.monotonic() < deadline:
            try:
                response = client.get(url)
                response.raise_for_status()

                if response.json().get("status") == "healthy":
                    return True

            except (httpx.HTTPError, ValueError):
                pass

            time.sleep(1)

    return False


def recover_service(item):
    """
    Start container, verify recovery and record result.
    """

    failure_id = item["failure_id"]
    service_name = item["service_name"]
    attempt_number = item["attempt_number"]

    config = ALLOWED_SERVICES[service_name]

    started_at = utc_now()
    timer_start = time.perf_counter()

    success = False
    error_message = None

    logger.warning(
        "RECOVERY_STARTED service=%s failure_id=%s attempt=%s",
        service_name,
        failure_id,
        attempt_number,
    )

    try:
        start_container(config["container"])

        success = verify_recovery(
            service_name,
            config["port"],
        )

        if not success:
            error_message = "Health verification timed out"

    except Exception as error:
        error_message = str(error)
        logger.exception(
            "Recovery action failed for %s",
            service_name,
        )

    completed_at = utc_now()

    recovery_time_ms = round(
        (time.perf_counter() - timer_start) * 1000
    )

    with SessionLocal() as db:
        db.add(
            RecoveryEvent(
                failure_id=failure_id,
                action="DOCKER_START",
                started_at=started_at,
                completed_at=completed_at,
                recovery_time_ms=recovery_time_ms,
                retry_count=attempt_number - 1,
                success=success,
            )
        )

        db.commit()

    if success:
        logger.info(
            "RECOVERY_SUCCESS service=%s duration_ms=%s",
            service_name,
            recovery_time_ms,
        )
    else:
        logger.error(
            "RECOVERY_FAILED service=%s error=%s",
            service_name,
            error_message,
        )


def main():
    logger.info("Recovery Controller started")

    while True:
        try:
            pending = find_pending_failures()

            for item in pending:
                service_name = item["service_name"]
                now = time.monotonic()

                previous = last_attempt.get(
                    item["failure_id"], 0
                )

                if now - previous < COOLDOWN_SECONDS:
                    continue

                last_attempt[item["failure_id"]] = now

                recover_service(item)

        except KeyboardInterrupt:
            logger.info("Recovery Controller stopped")
            break

        except Exception:
            logger.exception("Recovery controller error")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
