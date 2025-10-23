import logging
import structlog
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import base64
import json

from flask import Flask, request, jsonify, g, Response
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_socketio import SocketIO, emit, disconnect
import requests
from werkzeug.exceptions import HTTPException

from .config import config
from .models import (
    RegisterRequest, RegisterResponse, CameraState, LogEntry,
    AdminLoginRequest, AdminLoginResponse, AdminUserCreate, AdminUserResponse,
    AdminDashboardStats
)
from .auth import (
    verify_password, get_password_hash, create_access_token, verify_token,
    blacklist_token, get_current_admin_user, require_auth
)
from .metrics import get_metrics, increment_request_count, time_request

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

# Global state for WebSocket connections
websocket_clients: List[SocketIO] = []

# In-memory log storage
logs: List[Dict[str, Any]] = []

# In-memory admin user storage (in production, use a database)
admin_users: Dict[str, Dict[str, Any]] = {}

def create_app(config_name: str = 'default') -> Flask:
    """Flask application factory."""
    app = Flask(__name__)

    # Configure Flask app
    app.config['SECRET_KEY'] = config.jwt_secret_key
    app.config['JWT_SECRET_KEY'] = config.jwt_secret_key
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=config.jwt_access_token_expire_minutes)

    # Initialize extensions
    CORS(app, origins=config.cors_origins)
    jwt = JWTManager(app)
    socketio = SocketIO(app, cors_allowed_origins=config.socketio_cors_allowed_origins)

    # Initialize default admin user
    if config.admin_default_username not in admin_users:
        admin_users[config.admin_default_username] = {
            "username": config.admin_default_username,
            "hashed_password": get_password_hash(config.admin_default_password),
            "full_name": "System Administrator",
            "email": "admin@example.com",
            "is_active": True,
            "created_at": datetime.utcnow().isoformat()
        }

    # Register blueprints and routes
    register_routes(app, socketio)
    register_socketio_events(socketio)

    logger.info("Flask API Gateway application created", config=config_name)
    return app

def register_routes(app: Flask, socketio: SocketIO):
    """Register all routes with the Flask app."""

    @app.route('/health')
    def health_check():
        """Health check endpoint."""
        with time_request('GET', '/health'):
            increment_request_count('GET', '/health', '200')
            return jsonify({"status": "healthy"})

    @app.route('/metrics')
    def metrics():
        """Prometheus metrics endpoint."""
        return Response(get_metrics(), mimetype='text/plain; charset=utf-8')

    # Admin authentication routes
    @app.route('/admin/login', methods=['POST'])
    def admin_login():
        """Authenticate admin user and return JWT token."""
        with time_request('POST', '/admin/login'):
            try:
                login_data = AdminLoginRequest(**request.get_json())
            except Exception as e:
                increment_request_count('POST', '/admin/login', '400')
                return jsonify({"detail": "Invalid request data"}), 400

            user = admin_users.get(login_data.username)
            if not user or not verify_password(login_data.password, user["hashed_password"]):
                increment_request_count('POST', '/admin/login', '401')
                return jsonify({"detail": "Incorrect username or password"}), 401

            if not user.get("is_active"):
                increment_request_count('POST', '/admin/login', '401')
                return jsonify({"detail": "User account is disabled"}), 401

            access_token_expires = timedelta(minutes=config.jwt_access_token_expire_minutes)
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

            increment_request_count('POST', '/admin/login', '200')
            logger.info("Admin login successful", username=login_data.username)
            return jsonify({
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds()),
                "user": user_response
            })

    @app.route('/admin/logout', methods=['POST'])
    def admin_logout():
        """Logout admin user by blacklisting their token."""
        with time_request('POST', '/admin/logout'):
            try:
                current_user = get_current_admin_user()
                # Get the token from the Authorization header to blacklist it
                auth_header = request.headers.get('Authorization')
                if auth_header and auth_header.startswith('Bearer '):
                    token = auth_header.split(' ')[1]
                    blacklist_token(token)

                increment_request_count('POST', '/admin/logout', '200')
                logger.info("Admin logout", username=current_user["username"])
                return jsonify({"message": "Successfully logged out"})
            except HTTPException as e:
                increment_request_count('POST', '/admin/logout', str(e.code))
                raise

    # Admin user management routes
    @app.route('/admin/users', methods=['GET'])
    def get_admin_users():
        """Get all admin users."""
        with time_request('GET', '/admin/users'):
            try:
                get_current_admin_user()  # Check authentication
                users = []
                for user in admin_users.values():
                    users.append(AdminUserResponse(
                        username=user["username"],
                        full_name=user["full_name"],
                        email=user["email"],
                        is_active=user["is_active"],
                        created_at=user["created_at"]
                    ).dict())
                increment_request_count('GET', '/admin/users', '200')
                return jsonify(users)
            except HTTPException as e:
                increment_request_count('GET', '/admin/users', str(e.code))
                raise

    @app.route('/admin/users', methods=['POST'])
    def create_admin_user():
        """Create a new admin user."""
        with time_request('POST', '/admin/users'):
            try:
                get_current_admin_user()  # Check authentication
                user_data = AdminUserCreate(**request.get_json())

                if user_data.username in admin_users:
                    increment_request_count('POST', '/admin/users', '400')
                    return jsonify({"detail": "Username already exists"}), 400

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

                increment_request_count('POST', '/admin/users', '201')
                logger.info("Admin user created", username=user_data.username)
                return jsonify(AdminUserResponse(
                    username=new_user["username"],
                    full_name=new_user["full_name"],
                    email=new_user["email"],
                    is_active=new_user["is_active"],
                    created_at=new_user["created_at"]
                ).dict()), 201
            except HTTPException as e:
                increment_request_count('POST', '/admin/users', str(e.code))
                raise

    @app.route('/admin/users/<username>', methods=['DELETE'])
    def delete_admin_user(username):
        """Delete an admin user."""
        with time_request('DELETE', '/admin/users/{username}'):
            try:
                current_user = get_current_admin_user()

                if username not in admin_users:
                    increment_request_count('DELETE', '/admin/users/{username}', '404')
                    return jsonify({"detail": "User not found"}), 404

                if username == current_user["username"]:
                    increment_request_count('DELETE', '/admin/users/{username}', '400')
                    return jsonify({"detail": "Cannot delete your own account"}), 400

                del admin_users[username]
                increment_request_count('DELETE', '/admin/users/{username}', '200')
                logger.info("Admin user deleted", username=username, deleted_by=current_user["username"])
                return jsonify({"message": "User deleted successfully"})
            except HTTPException as e:
                increment_request_count('DELETE', '/admin/users/{username}', str(e.code))
                raise

    # Protected admin routes
    @app.route('/admin/dashboard/stats')
    def get_admin_dashboard_stats():
        """Get admin dashboard statistics."""
        with time_request('GET', '/admin/dashboard/stats'):
            try:
                get_current_admin_user()  # Check authentication

                # Check service health statuses
                services_status = {
                    "user_service": get_service_health_status("user-service", config.user_service_url),
                    "edge_processor": get_service_health_status("edge-processor", config.edge_processor_url),
                    "face_recognition": get_service_health_status("face-recognition", config.face_recognition_url),
                    "identity_tracker": get_service_health_status("identity-tracker", config.identity_tracker_url),
                    "promotions_display": get_service_health_status("promotions-display-service", config.promotions_display_url),
                    "recommendation_service": get_service_health_status("recommendation-service", config.recommendation_service_url)
                }

                # Determine overall server status
                unhealthy_services = [s for s in services_status.values() if s["status"] != "healthy"]
                server_status = "degraded" if unhealthy_services else "healthy"

                stats = AdminDashboardStats(
                    total_users=len(admin_users),
                    active_users=len([u for u in admin_users.values() if u["is_active"]]),
                    total_logs=len(logs),
                    websocket_clients=len(websocket_clients),
                    server_status=server_status
                )

                # Broadcast system status update
                broadcast_system_status({
                    "stats": stats.dict(),
                    "services": services_status
                })

                increment_request_count('GET', '/admin/dashboard/stats', '200')
                return jsonify(stats.dict())
            except HTTPException as e:
                increment_request_count('GET', '/admin/dashboard/stats', str(e.code))
                raise

    @app.route('/admin/logs')
    def get_admin_logs():
        """Get all logs for admin review."""
        with time_request('GET', '/admin/logs'):
            try:
                get_current_admin_user()  # Check authentication
                limit = request.args.get('limit', default=100, type=int)
                sorted_logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
                increment_request_count('GET', '/admin/logs', '200')
                return jsonify(sorted_logs[:limit])
            except HTTPException as e:
                increment_request_count('GET', '/admin/logs', str(e.code))
                raise

    # Public API routes
    @app.route('/register', methods=['POST'])
    def register():
        """Register a new customer."""
        with time_request('POST', '/register'):
            try:
                register_data = RegisterRequest(**request.get_json())
            except Exception as e:
                increment_request_count('POST', '/register', '400')
                return jsonify({"detail": "Invalid request data"}), 400

            try:
                response = requests.post(
                    f"{config.user_service_url}/register",
                    json={"name": register_data.name, "face_image_b64": register_data.face_image_b64},
                    timeout=10
                )
                if response.status_code != 200:
                    increment_request_count('POST', '/register', str(response.status_code))
                    logger.error("User service registration failed", status_code=response.status_code, response_text=response.text)
                    return jsonify({"detail": "Registration failed"}), response.status_code

                data = response.json()
                increment_request_count('POST', '/register', '200')
                logger.info("Registration successful", customer_id=data.get("customer_id"))
                return jsonify(RegisterResponse(message=data["message"], customer_id=data["customer_id"]).dict())
            except requests.Timeout:
                increment_request_count('POST', '/register', '504')
                logger.error("User service request timeout")
                return jsonify({"detail": "Service temporarily unavailable"}), 504
            except requests.ConnectionError:
                increment_request_count('POST', '/register', '503')
                logger.error("Failed to connect to user service - service may be down")
                return jsonify({"detail": "User service is currently unavailable"}), 503
            except requests.RequestException as e:
                increment_request_count('POST', '/register', '500')
                logger.error("Failed to connect to user service", error=str(e))
                return jsonify({"detail": "Internal server error"}), 500

    # Dashboard routes
    @app.route('/logs', methods=['POST'])
    def add_log_entry():
        """Add a new log entry and broadcast to WebSocket clients."""
        with time_request('POST', '/logs'):
            try:
                log_data = LogEntry(**request.get_json())
                if not log_data.timestamp:
                    log_data.timestamp = datetime.utcnow().isoformat()

                log_entry = log_data.dict()
                logs.append(log_entry)

                # Broadcast to WebSocket clients
                broadcast_log_entry(log_entry)

                increment_request_count('POST', '/logs', '200')
                logger.info("Log entry added", level=log_entry['level'], message=log_entry['message'])
                return jsonify(log_entry)
            except Exception as e:
                increment_request_count('POST', '/logs', '400')
                return jsonify({"detail": "Invalid log entry data"}), 400

    @app.route('/logs', methods=['GET'])
    def get_logs():
        """Get recent event logs."""
        with time_request('GET', '/logs'):
            try:
                limit = request.args.get('limit', default=50, type=int)
                sorted_logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
                increment_request_count('GET', '/logs', '200')
                return jsonify(sorted_logs[:limit])
            except Exception as e:
                increment_request_count('GET', '/logs', '500')
                logger.error("Error fetching logs", error=str(e))
                return jsonify({"detail": "Internal server error"}), 500

    @app.route('/cameras', methods=['GET'])
    def get_cameras():
        """Get list of cameras from edge processor."""
        with time_request('GET', '/cameras'):
            try:
                response = requests.get(f"{config.edge_processor_url}/cameras", timeout=10)
                if response.status_code != 200:
                    increment_request_count('GET', '/cameras', str(response.status_code))
                    logger.error("Edge processor cameras request failed", status_code=response.status_code, response_text=response.text)
                    return jsonify({"detail": "Failed to fetch cameras"}), response.status_code

                cameras_data = response.json()
                cameras = []
                for cam_data in cameras_data:
                    cameras.append(CameraState(
                        id=cam_data["id"],
                        name=cam_data["name"],
                        status=cam_data["status"],
                        last_seen=cam_data["last_seen"],
                        location=cam_data.get("location", "")
                    ).dict())

                increment_request_count('GET', '/cameras', '200')
                return jsonify(cameras)
            except requests.Timeout:
                increment_request_count('GET', '/cameras', '504')
                logger.error("Edge processor request timeout")
                return jsonify({"detail": "Edge processor service temporarily unavailable"}), 504
            except requests.ConnectionError:
                increment_request_count('GET', '/cameras', '503')
                logger.error("Failed to connect to edge processor - service may be down")
                return jsonify({"detail": "Edge processor service is currently unavailable"}), 503
            except requests.RequestException as e:
                increment_request_count('GET', '/cameras', '500')
                logger.error("Failed to connect to edge processor", error=str(e))
                return jsonify({"detail": "Internal server error"}), 500
            except Exception as e:
                increment_request_count('GET', '/cameras', '500')
                logger.error("Error fetching cameras", error=str(e))
                return jsonify({"detail": "Internal server error"}), 500

    @app.route('/alerts/count', methods=['GET'])
    def get_alerts_count():
        """Get count of active alerts."""
        with time_request('GET', '/alerts/count'):
            try:
                # For now, return mock data - in production, this could proxy to a monitoring service
                # or check logs for error conditions
                alert_count = 0

                # Check for recent error logs as a simple alert mechanism
                recent_logs = [log for log in logs if log.get('level') in ['ERROR', 'WARNING']]
                if recent_logs:
                    alert_count = len(recent_logs)

                increment_request_count('GET', '/alerts/count', '200')
                return jsonify({"count": alert_count})
            except Exception as e:
                increment_request_count('GET', '/alerts/count', '500')
                logger.error("Error fetching alerts count", error=str(e))
                return jsonify({"detail": "Internal server error"}), 500

    # Error handlers
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        """Handle HTTP exceptions."""
        return jsonify({"detail": e.description}), e.code

    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle general exceptions."""
        logger.error("Unhandled exception", error=str(e))
        return jsonify({"detail": "Internal server error"}), 500

def register_socketio_events(socketio: SocketIO):
    """Register SocketIO event handlers."""

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        websocket_clients.append(request.sid)
        logger.info("WebSocket client connected", client_count=len(websocket_clients))
        emit('connected', {'status': 'connected'})

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        if request.sid in websocket_clients:
            websocket_clients.remove(request.sid)
        logger.info("WebSocket client disconnected", client_count=len(websocket_clients))

    @socketio.on('dashboard_subscribe')
    def handle_dashboard_subscribe():
        """Handle dashboard subscription."""
        emit('subscription_confirmed', {'type': 'dashboard'})

    @socketio.on('dashboard_connect')
    def handle_dashboard_connect():
        """Handle dashboard WebSocket connection for real-time updates."""
        websocket_clients.append(request.sid)
        logger.info("Dashboard WebSocket client connected", client_count=len(websocket_clients))
        emit('dashboard_connected', {
            'status': 'connected',
            'message': 'Real-time dashboard updates enabled'
        })

    @socketio.on('dashboard_disconnect')
    def handle_dashboard_disconnect():
        """Handle dashboard WebSocket disconnection."""
        if request.sid in websocket_clients:
            websocket_clients.remove(request.sid)
        logger.info("Dashboard WebSocket client disconnected", client_count=len(websocket_clients))
        emit('dashboard_disconnected', {
            'status': 'disconnected',
            'message': 'Real-time dashboard updates disabled'
        })

# Utility functions for broadcasting
def broadcast_dashboard_update(update_type: str, data: Dict[str, Any]):
    """Broadcast updates to all connected dashboard clients."""
    message = {
        "type": update_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }
    socketio.emit('dashboard_update', message)

def broadcast_log_entry(log_entry: Dict[str, Any]):
    """Broadcast a log entry to all connected dashboard clients."""
    socketio.emit('new_log', log_entry)

def broadcast_system_status(status_data: Dict[str, Any]):
    """Broadcast system status updates to dashboard clients."""
    socketio.emit('system_status', status_data)

def get_service_health_status(service_name: str, service_url: str) -> Dict[str, Any]:
    """Check health status of a service."""
    try:
        response = requests.get(f"{service_url}/health", timeout=5)
        return {
            "service": service_name,
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "response_time": response.elapsed.total_seconds(),
            "last_checked": datetime.utcnow().isoformat()
        }
    except requests.RequestException as e:
        return {
            "service": service_name,
            "status": "unreachable",
            "error": str(e),
            "last_checked": datetime.utcnow().isoformat()
        }

def make_service_request(method: str, url: str, **kwargs) -> requests.Response:
    """Make HTTP request to a service with consistent error handling and logging."""
    try:
        timeout = kwargs.pop('timeout', 10)
        response = requests.request(method, url, timeout=timeout, **kwargs)
        logger.debug(f"Service request: {method} {url} -> {response.status_code}")
        return response
    except requests.RequestException as e:
        logger.error(f"Service request failed: {method} {url}", error=str(e))
        raise