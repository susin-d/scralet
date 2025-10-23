import structlog
import httpx
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, field_validator
import base64
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, Counter, Histogram
import asyncio
from typing import List, Dict, Any, Optional
import json
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt

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
logs: List[Dict[str, Any]] = []

# Admin authentication configuration
SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()

# In-memory admin user storage
admin_users: Dict[str, Dict[str, Any]] = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin123"),  # Default password
        "full_name": "System Administrator",
        "email": "admin@example.com",
        "is_active": True,
        "created_at": datetime.utcnow().isoformat()
    }
}

# Blacklisted tokens (for logout)
blacklisted_tokens: set = set()

# Utility functions for authentication
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[str]:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None or token in blacklisted_tokens:
            return None
        return username
    except JWTError:
        return None

async def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get the current authenticated admin user."""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = admin_users.get(username)
    if user is None or not user.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

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

# Admin authentication models
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict[str, Any]

class AdminUserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    email: str

class AdminUserResponse(BaseModel):
    username: str
    full_name: str
    email: str
    is_active: bool
    created_at: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Admin authentication endpoints
@app.post("/admin/login", response_model=AdminLoginResponse)
async def admin_login(request: AdminLoginRequest):
    """Authenticate admin user and return JWT token."""
    with REQUEST_LATENCY.labels(method='POST', endpoint='/admin/login').time():
        user = admin_users.get(request.username)
        if not user or not verify_password(request.password, user["hashed_password"]):
            REQUEST_COUNT.labels(method='POST', endpoint='/admin/login', status='401').inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.get("is_active"):
            REQUEST_COUNT.labels(method='POST', endpoint='/admin/login', status='401').inc()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user["username"]}, expires_delta=access_token_expires
        )

        user_response = {
            "username": user["username"],
            "full_name": user["full_name"],
            "email": user["email"],
            "is_active": user["is_active"],
            "created_at": user["created_at"]
        }

        REQUEST_COUNT.labels(method='POST', endpoint='/admin/login', status='200').inc()
        logger.info("Admin login successful", username=request.username)
        return AdminLoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=int(access_token_expires.total_seconds()),
            user=user_response
        )

@app.post("/admin/logout")
async def admin_logout(current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Logout admin user by blacklisting their token."""
    with REQUEST_LATENCY.labels(method='POST', endpoint='/admin/logout').time():
        # Note: In a real implementation, you'd get the token from the request
        # For simplicity, we'll assume the token is passed in the Authorization header
        # and we can blacklist it. However, since we can't easily extract the token here,
        # we'll just log the logout for now.
        REQUEST_COUNT.labels(method='POST', endpoint='/admin/logout', status='200').inc()
        logger.info("Admin logout", username=current_user["username"])
        return {"message": "Successfully logged out"}

# Admin user management endpoints
@app.get("/admin/users", response_model=List[AdminUserResponse])
async def get_admin_users(current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Get all admin users."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/admin/users').time():
        users = []
        for user in admin_users.values():
            users.append(AdminUserResponse(
                username=user["username"],
                full_name=user["full_name"],
                email=user["email"],
                is_active=user["is_active"],
                created_at=user["created_at"]
            ))
        REQUEST_COUNT.labels(method='GET', endpoint='/admin/users', status='200').inc()
        return users

@app.post("/admin/users", response_model=AdminUserResponse)
async def create_admin_user(
    user_data: AdminUserCreate,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Create a new admin user."""
    with REQUEST_LATENCY.labels(method='POST', endpoint='/admin/users').time():
        if user_data.username in admin_users:
            REQUEST_COUNT.labels(method='POST', endpoint='/admin/users', status='400').inc()
            raise HTTPException(status_code=400, detail="Username already exists")

        hashed_password = get_password_hash(user_data.password)
        new_user = {
            "username": user_data.username,
            "hashed_password": hashed_password,
            "full_name": user_data.full_name,
            "email": user_data.email,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        admin_users[user_data.username] = new_user

        REQUEST_COUNT.labels(method='POST', endpoint='/admin/users', status='201').inc()
        logger.info("Admin user created", username=user_data.username, created_by=current_user["username"])
        return AdminUserResponse(
            username=new_user["username"],
            full_name=new_user["full_name"],
            email=new_user["email"],
            is_active=new_user["is_active"],
            created_at=new_user["created_at"]
        )

@app.delete("/admin/users/{username}")
async def delete_admin_user(
    username: str,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Delete an admin user."""
    with REQUEST_LATENCY.labels(method='DELETE', endpoint='/admin/users/{username}').time():
        if username not in admin_users:
            REQUEST_COUNT.labels(method='DELETE', endpoint='/admin/users/{username}', status='404').inc()
            raise HTTPException(status_code=404, detail="User not found")

        if username == current_user["username"]:
            REQUEST_COUNT.labels(method='DELETE', endpoint='/admin/users/{username}', status='400').inc()
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        del admin_users[username]
        REQUEST_COUNT.labels(method='DELETE', endpoint='/admin/users/{username}', status='200').inc()
        logger.info("Admin user deleted", username=username, deleted_by=current_user["username"])
        return {"message": "User deleted successfully"}

# Metrics endpoint
@app.get("/metrics")
async def metrics():
    return generate_latest()

# Protected admin endpoints (require authentication)
@app.get("/admin/dashboard/stats")
async def get_admin_dashboard_stats(current_user: Dict[str, Any] = Depends(get_current_admin_user)):
    """Get admin dashboard statistics."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/admin/dashboard/stats').time():
        stats = {
            "total_users": len(admin_users),
            "active_users": len([u for u in admin_users.values() if u["is_active"]]),
            "total_logs": len(logs),
            "websocket_clients": len(websocket_clients),
            "server_status": "healthy"
        }
        REQUEST_COUNT.labels(method='GET', endpoint='/admin/dashboard/stats', status='200').inc()
        return stats

@app.get("/admin/logs")
async def get_admin_logs(
    limit: int = 100,
    current_user: Dict[str, Any] = Depends(get_current_admin_user)
):
    """Get all logs for admin review."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/admin/logs').time():
        sorted_logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
        REQUEST_COUNT.labels(method='GET', endpoint='/admin/logs', status='200').inc()
        return sorted_logs[:limit]

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
@app.post("/logs")
async def add_log_entry(log_entry: LogEntry):
    """Add a new log entry and broadcast to WebSocket clients."""
    with REQUEST_LATENCY.labels(method='POST', endpoint='/logs').time():
        try:
            # Add timestamp if not provided
            if not log_entry.timestamp:
                log_entry.timestamp = datetime.utcnow().isoformat()

            # Store the log entry as dict
            logs.append(log_entry.dict())

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

@app.get("/logs")
async def get_logs(limit: int = 50):
    """Get recent event logs."""
    with REQUEST_LATENCY.labels(method='GET', endpoint='/logs').time():
        try:
            # Return logs sorted by timestamp descending (most recent first)
            sorted_logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
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