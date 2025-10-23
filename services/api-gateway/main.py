import structlog
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, field_validator
import base64
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import asyncio
from typing import List, Dict, Any
import json
from datetime import datetime

from config import config

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Prometheus metrics
REQUEST_COUNT = Counter('api_gateway_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('api_gateway_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])

app = FastAPI(title="API Gateway", version="1.0.0")

# Global state for WebSocket connections
websocket_clients: List[WebSocket] = []

# In-memory log storage
logs: List[LogEntry] = []

# Pydantic models
class RegisterRequest(BaseModel):
    name: str
    face_image_b64: str

    @field_validator('face_image_b64')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 string')

class RegisterResponse(BaseModel):
    message: str
    customer_id: str

class CameraState(BaseModel):
    id: str
    name: str
    status: str
    last_seen: str
    location: str = ""

class LogEntry(BaseModel):
    timestamp: str
    level: str
    message: str
    camera: str = ""

class SocketStatus(BaseModel):
    connected_clients: int
    last_update: str
    status: str

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return generate_latest()

# API endpoints
@app.post("/register", response_model=RegisterResponse)
async def register(request: RegisterRequest):
    with REQUEST_LATENCY.labels(method='POST', endpoint='/register').time():
        logger.info("Registration request received", name=request.name)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{config.user_service_url}/register",
                    json={"name": request.name, "face_image_b64": request.face_image_b64}
                )
                if response.status_code != 200:
                    REQUEST_COUNT.labels(method='POST', endpoint='/register', status=str(response.status_code)).inc()
                    logger.error("User service registration failed", status_code=response.status_code, response=response.text)
                    raise HTTPException(status_code=response.status_code, detail="Registration failed")
                data = response.json()
                REQUEST_COUNT.labels(method='POST', endpoint='/register', status='200').inc()
                logger.info("Registration successful", customer_id=data.get("customer_id"))
                return RegisterResponse(message=data["message"], customer_id=data["customer_id"])
        except httpx.RequestError as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/register', status='500').inc()
            logger.error("Failed to connect to user service", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/register', status='500').inc()
            logger.error("Unexpected error in registration", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

# Dashboard endpoints
@app.post("/logs", response_model=LogEntry)
async def add_log_entry(log_entry: LogEntry):
    """Add a new log entry and broadcast to WebSocket clients."""
    with REQUEST_LATENCY.labels(method='POST', endpoint='/logs').time():
        try:
            # Add timestamp if not provided
            if not log_entry.timestamp:
                log_entry.timestamp = datetime.utcnow().isoformat()

            # Store the log entry
            logs.append(log_entry)

            # Broadcast the new log entry to all connected WebSocket clients
            await broadcast_dashboard_update("new_log", log_entry.dict())

            REQUEST_COUNT.labels(method='POST', endpoint='/logs', status='200').inc()
            logger.info("Log entry added", level=log_entry.level, message=log_entry.message, camera=log_entry.camera)
            return log_entry
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/logs', status='500').inc()
            logger.error("Error adding log entry", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

# Dashboard endpoints
@app.get("/cameras", response_model=List[CameraState])
async def get_cameras():
    """Get list of cameras from edge processor."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/cameras').time():
        try:
            async with httpx.AsyncClient() as client:
                # For now, we'll simulate camera data since edge-processor doesn't have a cameras list endpoint
                # In production, this would call edge-processor to get actual camera states
                cameras = [
                    CameraState(
                        id="cam_001",
                        name="Entrance Camera",
                        status="online",
                        last_seen=datetime.utcnow().isoformat(),
                        location="Main Entrance"
                    ),
                    CameraState(
                        id="cam_002",
                        name="Checkout Camera",
                        status="online",
                        last_seen=datetime.utcnow().isoformat(),
                        location="Checkout Area"
                    )
                ]
                REQUEST_COUNT.labels(method='GET', endpoint='/cameras', status='200').inc()
                return cameras
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint='/cameras', status='500').inc()
            logger.error("Error fetching cameras", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/logs", response_model=List[LogEntry])
async def get_logs(limit: int = 50):
    """Get recent event logs."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/logs').time():
        try:
            # Return logs sorted by timestamp descending (most recent first)
            sorted_logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)
            REQUEST_COUNT.labels(method='GET', endpoint='/logs', status='200').inc()
            return sorted_logs[:limit]
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint='/logs', status='500').inc()
            logger.error("Error fetching logs", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/alerts/count")
async def get_alerts_count():
    """Get count of active alerts."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/alerts/count').time():
        try:
            # For now, return mock count. In production, this would check for actual alerts
            alert_count = 2  # Mock alert count
            REQUEST_COUNT.labels(method='GET', endpoint='/alerts/count', status='200').inc()
            return {"count": alert_count}
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint='/alerts/count', status='500').inc()
            logger.error("Error fetching alerts count", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates including logs."""
    await websocket.accept()
    websocket_clients.append(websocket)
    logger.info("Dashboard WebSocket client connected", client_count=len(websocket_clients))

    try:
        while True:
            # Keep connection alive and wait for client messages
            data = await websocket.receive_text()
            # For now, just echo back. In production, this could handle client commands
            await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        websocket_clients.remove(websocket)
        logger.info("Dashboard WebSocket client disconnected", client_count=len(websocket_clients))
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        if websocket in websocket_clients:
            websocket_clients.remove(websocket)

async def broadcast_dashboard_update(update_type: str, data: Dict[str, Any]):
    """Broadcast updates to all connected dashboard clients."""
    message = {
        "type": update_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }

    disconnected_clients = []
    for client in websocket_clients[:]:  # Copy list to avoid modification during iteration
        try:
            await client.send_json(message)
        except Exception as e:
            logger.warning("Failed to send update to client", error=str(e))
            disconnected_clients.append(client)

    # Clean up disconnected clients
    for client in disconnected_clients:
        if client in websocket_clients:
            websocket_clients.remove(client)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)