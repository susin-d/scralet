import os
from typing import Optional

class Config:
    """Configuration class for Flask API Gateway."""

    def __init__(self):
        # Service URLs
        self.user_service_url: str = os.getenv('USER_SERVICE_URL', 'http://user-service:8001')
        self.edge_processor_url: str = os.getenv('EDGE_PROCESSOR_URL', 'http://edge-processor:8000')
        self.face_recognition_url: str = os.getenv('FACE_RECOGNITION_URL', 'http://face-recognition:8000')
        self.identity_tracker_url: str = os.getenv('IDENTITY_TRACKER_URL', 'http://identity-tracker:8000')
        self.promotions_display_url: str = os.getenv('PROMOTIONS_DISPLAY_URL', 'http://promotions-display-service:8002')
        self.recommendation_service_url: str = os.getenv('RECOMMENDATION_SERVICE_URL', 'http://recommendation-service:8000')

        # JWT Configuration
        self.jwt_secret_key: str = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
        self.jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
        self.jwt_access_token_expire_minutes: int = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', '30'))

        # Logging Configuration
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')

        # Flask Configuration
        self.flask_env: str = os.getenv('FLASK_ENV', 'development')
        self.flask_debug: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
        self.flask_host: str = os.getenv('FLASK_HOST', '0.0.0.0')
        self.flask_port: int = int(os.getenv('FLASK_PORT', '8000'))

        # CORS Configuration
        self.cors_origins: list = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:5173').split(',')

        # SocketIO Configuration
        self.socketio_cors_allowed_origins: list = os.getenv('SOCKETIO_CORS_ALLOWED_ORIGINS', '*').split(',')

        # Admin Configuration
        self.admin_default_username: str = os.getenv('ADMIN_DEFAULT_USERNAME', 'admin')
        self.admin_default_password: str = os.getenv('ADMIN_DEFAULT_PASSWORD', 'admin123')

# Global config instance
config = Config()