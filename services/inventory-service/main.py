
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Inventory Service",
    version="1.0.0"
)


class Product(BaseModel):
    id: int
    name: str
    quantity: int = Field(ge=0)


inventory = {
    1: Product(id=1, name="Laptop", quantity=10),
    2: Product(id=2, name="Keyboard", quantity=25),
    3: Product(id=3, name="Mouse", quantity=40),
}


@app.get("/")
def home():
    return {"message": "Inventory Service is running"}


@app.get("/health")
def health_check():
    return {
        "service": "inventory-service",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/inventory")
def list_inventory():
    return list(inventory.values())


@app.get("/inventory/{product_id}")
def get_product(product_id: int):
    product = inventory.get(product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product
