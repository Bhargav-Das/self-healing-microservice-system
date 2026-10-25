
from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(
    title="Order Service",
    description="Order microservice for the self-healing system",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "message": "Order Service is running"
    }

@app.get("/health")
def health_check():
    return {
        "service": "order-service",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/orders")
def get_orders():
    return {
        "orders": [],
        "message": "Order API is working"
    }
