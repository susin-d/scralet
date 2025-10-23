from pydantic import BaseModel, field_validator
from typing import Dict, Any, Optional
import base64


# Request/Response models for validation
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


class AdminDashboardStats(BaseModel):
    total_users: int
    active_users: int
    total_logs: int
    websocket_clients: int
    server_status: str