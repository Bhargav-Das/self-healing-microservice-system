
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(
    title="Notification Service",
    version="1.0.0"
)


class NotificationRequest(BaseModel):
    user: str = Field(min_length=1)
    message: str = Field(min_length=1)


@app.get("/")
def home():
    return {
        "message": "Notification Service is running"
    }


@app.get("/health")
def health_check():
    return {
        "service": "notification-service",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.post("/notifications", status_code=202)
def send_notification(data: NotificationRequest):
    return {
        "user": data.user,
        "message": data.message,
        "status": "accepted",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
