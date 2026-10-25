
import asyncio
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from database.db import SessionLocal
from database.models import (
    Service,
    HealthCheck,
    FailureEvent,
)

logger = logging.getLogger("monitoring")

CHECK_INTERVAL = 5
FAILURE_THRESHOLD = 3
REQUEST_TIMEOUT = 2.0

# Tracks consecutive failures during this process lifetime
failure_counts = {}


def utc_now():
    return datetime.now(timezone.utc)


def register_default_services():
    """
    Register the three local Docker services.
    Existing registrations are preserved.
    """

    defaults = [
        {
            "name": "order-service",
            "url": "http://order-service:8001",
            "container_name": "order-service",
        },
        {
            "name": "inventory-service",
            "url": "http://inventory-service:8002",
            "container_name": "inventory-service",
        },
        {
            "name": "notification-service",
            "url": "http://notification-service:8003",
            "container_name": "notification-service",
        },
    ]

    with SessionLocal() as db:
        for item in defaults:
            existing = db.scalar(
                select(Service).where(
                    Service.name == item["name"]
                )
            )

            if existing is None:
                db.add(
                    Service(
                        name=item["name"],
                        url=item["url"],
                        container_name=item["container_name"],
                        status="UNKNOWN",
                    )
                )
            else:
                existing.url = item["url"]
                existing.container_name = item["container_name"]

        db.commit()

    logger.info("Default services registered")


def load_services():
    """
    Retrieve registered services from PostgreSQL.
    """

    with SessionLocal() as db:
        services = db.scalars(
            select(Service).order_by(Service.id)
        ).all()

        return [
            {
                "id": service.id,
                "name": service.name,
                "url": service.url,
            }
            for service in services
        ]


async def check_service(client, service):
    """
    Send one health-check request and record its result.
    """

    service_id = service["id"]
    service_name = service["name"]

    started = time.perf_counter()
    healthy = False
    error_message = None

    try:
        response = await client.get(
            f"{service['url'].rstrip('/')}/health",
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

        healthy = (
            payload.get("status") == "healthy"
        )

        if not healthy:
            error_message = "Health endpoint returned unhealthy"

    except (httpx.HTTPError, ValueError) as error:
        error_message = str(error)

    response_time_ms = round(
        (time.perf_counter() - started) * 1000
    )

    with SessionLocal() as db:
        db_service = db.get(Service, service_id)

        if db_service is None:
            return

        db.add(
            HealthCheck(
                service_id=service_id,
                status="HEALTHY" if healthy else "FAILED",
                response_time_ms=response_time_ms,
                checked_at=utc_now(),
            )
        )

        if healthy:
            failure_counts[service_id] = 0

            if db_service.status == "UNHEALTHY":
                active_failure = db.scalar(
                    select(FailureEvent)
                    .where(
                        FailureEvent.service_id == service_id,
                        FailureEvent.status == "OPEN",
                    )
                    .order_by(FailureEvent.id.desc())
                )

                if active_failure:
                    active_failure.status = "RESOLVED"

                logger.info(
                    "SERVICE_RECOVERED service=%s",
                    service_name,
                )

            db_service.status = "HEALTHY"

        else:
            count = failure_counts.get(service_id, 0) + 1
            failure_counts[service_id] = count

            logger.warning(
                "HEALTH_CHECK_FAILED service=%s count=%s error=%s",
                service_name,
                count,
                error_message,
            )

            if count >= FAILURE_THRESHOLD:
                if db_service.status != "UNHEALTHY":
                    db_service.status = "UNHEALTHY"

                    db.add(
                        FailureEvent(
                            service_id=service_id,
                            failure_type="HEALTH_CHECK_FAILURE",
                            error_message=error_message,
                            detected_at=utc_now(),
                            status="OPEN",
                        )
                    )

                    logger.error(
                        "SERVICE_UNHEALTHY service=%s",
                        service_name,
                    )

        db.commit()


async def monitoring_loop():
    """
    Continuously monitor registered services.
    """

    logger.info("Monitoring loop started")

    async with httpx.AsyncClient() as client:
        while True:
            try:
                services = await asyncio.to_thread(
                    load_services
                )

                await asyncio.gather(
                    *[
                        check_service(client, service)
                        for service in services
                    ]
                )

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception("Monitoring cycle failed")

            await asyncio.sleep(CHECK_INTERVAL)
