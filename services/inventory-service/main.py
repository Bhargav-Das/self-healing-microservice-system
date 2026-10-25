
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database.db import get_db
from database.models import InventoryItem


app = FastAPI(
    title="Inventory Service",
    version="2.0.0"
)


class InventoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0)


@app.get("/")
def home():
    return {"message": "Inventory Service is running"}


@app.get("/health")
def health():
    return {
        "service": "inventory-service",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/inventory", status_code=201)
def create_inventory_item(
    data: InventoryCreate,
    db: Session = Depends(get_db)
):
    item = InventoryItem(
        name=data.name,
        quantity=data.quantity
    )

    db.add(item)
    db.commit()
    db.refresh(item)

    return {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity
    }


@app.get("/inventory")
def list_inventory(db: Session = Depends(get_db)):
    items = db.query(InventoryItem).order_by(
        InventoryItem.id
    ).all()

    return [
        {
            "id": item.id,
            "name": item.name,
            "quantity": item.quantity
        }
        for item in items
    ]


@app.get("/inventory/{item_id}")
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db)
):
    item = db.get(InventoryItem, item_id)

    if item is None:
        raise HTTPException(
            status_code=404,
            detail="Inventory item not found"
        )

    return {
        "id": item.id,
        "name": item.name,
        "quantity": item.quantity
    }
