
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import Order


app = FastAPI(
    title="Order Service",
    version="2.0.0"
)


class OrderCreate(BaseModel):
    product_name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(gt=0)


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
    db: Session = Depends(get_db)
):
    order = Order(
        product_name=data.product_name,
        quantity=data.quantity,
        status="CREATED"
    )

    db.add(order)
    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "status": order.status
    }


@app.get("/orders")
def list_orders(db: Session = Depends(get_db)):
    orders = db.query(Order).order_by(Order.id).all()

    return [
        {
            "id": order.id,
            "product_name": order.product_name,
            "quantity": order.quantity,
            "status": order.status
        }
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

    return {
        "id": order.id,
        "product_name": order.product_name,
        "quantity": order.quantity,
        "status": order.status
    }
