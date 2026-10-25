
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Order, NotificationOutbox


app = FastAPI(
    title="Order Service",
    version="3.0.0"
)


class OrderCreate(BaseModel):
    product_name: str = Field(
        min_length=1,
        max_length=100
    )
    quantity: int = Field(gt=0)


def order_response(order, replayed=False):
    return {
        "id": order.id,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "status": order.status,
        "replayed": replayed
    }


@app.get("/")
def home():
    return {"message": "Order Service is running"}


@app.get("/health")
def health():
    return {
        "service": "order-service",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/orders", status_code=201)
def create_order(
    data: OrderCreate,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key")
    ],
    db: Session = Depends(get_db)
):
    key = idempotency_key.strip()

    if not key or len(key) > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid Idempotency-Key"
        )

    existing = db.scalar(
        select(Order).where(
            Order.idempotency_key == key
        )
    )

    if existing:
        if (
            existing.product_name != data.product_name
            or existing.quantity != data.quantity
        ):
            raise HTTPException(
                status_code=409,
                detail="Idempotency key reused with different data"
            )

        return order_response(existing, replayed=True)

    order = Order(
        product_name=data.product_name,
        quantity=data.quantity,
        status="CREATED",
        idempotency_key=key
    )

    try:
        db.add(order)
        db.flush()

        notification = NotificationOutbox(
            order_id=order.id,
            status="PENDING",
            attempts=0
        )

        db.add(notification)

        # Both records are committed together
        db.commit()
        db.refresh(order)

    except IntegrityError:
        db.rollback()

        existing = db.scalar(
            select(Order).where(
                Order.idempotency_key == key
            )
        )

        if existing is None:
            raise HTTPException(
                status_code=409,
                detail="Order creation conflict"
            )

        if (
            existing.product_name != data.product_name
            or existing.quantity != data.quantity
        ):
            raise HTTPException(
                status_code=409,
                detail="Idempotency key reused with different data"
            )

        return order_response(existing, replayed=True)

    return order_response(order, replayed=False)


@app.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    orders = db.scalars(
        select(Order).order_by(Order.id)
    ).all()

    return [
        order_response(order)
        for order in orders
    ]


@app.get("/orders/{order_id}")
def get_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    order = db.get(Order, order_id)

    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found"
        )

    return order_response(order)
