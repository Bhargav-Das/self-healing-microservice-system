
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import (
    Service,
    HealthCheck,
    FailureEvent,
)

from monitor import (
    monitoring_loop,
    register_default_services,
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_default_services()

    task = asyncio.create_task(monitoring_loop())

    yield

    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Self-Healing Monitoring Service",
    description="Health monitoring and failure detection APIs",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
def monitor_health():
    return {
        "service": "monitoring-service",
        "status": "healthy",
    }


@app.get("/services")
def list_services(db: Session = Depends(get_db)):
    services = db.scalars(
        select(Service).order_by(Service.id)
    ).all()

    return [
        {
            "id": service.id,
            "name": service.name,
            "url": service.url,
            "status": service.status,
        }
        for service in services
    ]


@app.get("/services/{service_id}/status")
def service_status(
    service_id: int,
    db: Session = Depends(get_db),
):
    service = db.get(Service, service_id)

    if service is None:
        raise HTTPException(
            status_code=404,
            detail="Service not found",
        )

    return {
        "id": service.id,
        "name": service.name,
        "status": service.status,
    }


@app.get("/health-checks")
def health_check_history(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    limit = max(1, min(limit, 500))

    checks = db.scalars(
        select(HealthCheck)
        .order_by(HealthCheck.id.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": check.id,
            "service_id": check.service_id,
            "status": check.status,
            "response_time_ms": check.response_time_ms,
            "checked_at": check.checked_at,
        }
        for check in checks
    ]


@app.get("/failures")
def list_failures(db: Session = Depends(get_db)):
    failures = db.scalars(
        select(FailureEvent)
        .order_by(FailureEvent.id.desc())
        .limit(100)
    ).all()

    return [
        {
            "id": failure.id,
            "service_id": failure.service_id,
            "failure_type": failure.failure_type,
            "error_message": failure.error_message,
            "detected_at": failure.detected_at,
            "status": failure.status,
        }
        for failure in failures
    ]
