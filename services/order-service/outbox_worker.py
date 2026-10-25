
import logging
import os
import time
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy import select, or_

from database.db import SessionLocal
from database.models import NotificationOutbox, Order


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)

logger = logging.getLogger("outbox-worker")

NOTIFICATION_URL = os.getenv(
    "NOTIFICATION_URL",
    "http://notification-service:8003"
)

MAX_ATTEMPTS = 5
POLL_INTERVAL = 3


def utc_now():
    return datetime.now(timezone.utc)


def process_outbox():
    with SessionLocal() as db:

        now = utc_now()

        jobs = db.scalars(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.status.in_(
                    ["PENDING", "RETRY"]
                ),
                or_(
                    NotificationOutbox.next_attempt_at.is_(None),
                    NotificationOutbox.next_attempt_at <= now
                )
            )
            .order_by(NotificationOutbox.id)
            .limit(10)
        ).all()

        for job in jobs:
            order = db.get(Order, job.order_id)

            if order is None:
                job.status = "FAILED"
                job.last_error = "Order not found"
                db.commit()
                continue

            try:
                response = httpx.post(
                    f"{NOTIFICATION_URL}/notifications",
                    json={
                        "user": "demo-user",
                        "message": (
                            f"Order {order.id} created for "
                            f"{order.product_name}"
                        )
                    },
                    timeout=2.0
                )

                response.raise_for_status()

                job.status = "DELIVERED"
                job.delivered_at = utc_now()
                job.next_attempt_at = None
                job.last_error = None

                logger.info(
                    "NOTIFICATION_DELIVERED order_id=%s",
                    order.id
                )

            except httpx.HTTPError as error:
                job.attempts += 1
                job.last_error = str(error)

                if job.attempts >= MAX_ATTEMPTS:
                    job.status = "FAILED"
                    job.next_attempt_at = None
                else:
                    delay = min(2 ** job.attempts, 60)

                    job.next_attempt_at = (
                        utc_now() + timedelta(seconds=delay)
                    )

                    job.status = "RETRY"

                logger.warning(
                    "NOTIFICATION_RETRY order_id=%s attempts=%s",
                    order.id,
                    job.attempts
                )

            db.commit()


def main():
    logger.info("Outbox worker started")

    while True:
        try:
            process_outbox()

        except Exception:
            logger.exception("Outbox processing failed")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
