
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base


def utc_now():
    return datetime.now(timezone.utc)


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    url: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    container_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="UNKNOWN"
    )


class HealthCheck(Base):
    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    response_time_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )


class FailureEvent(Base):
    __tablename__ = "failure_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id"), nullable=False
    )
    failure_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    status: Mapped[str] = mapped_column(
        String(30), default="OPEN"
    )


class RecoveryEvent(Base):
    __tablename__ = "recovery_events"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    failure_id: Mapped[int] = mapped_column(
        ForeignKey("failure_events.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recovery_time_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0
    )
    success: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    product_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), default="CREATED"
    )

    # Prevent duplicate orders on repeated requests
    idempotency_key: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True
    )

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    quantity: Mapped[int] = mapped_column(
        Integer, nullable=False
    )


class NotificationOutbox(Base):
    __tablename__ = "notification_outbox"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"),
        nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="PENDING",
        nullable=False
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    next_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
