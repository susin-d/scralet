import os
from typing import Optional

class Config:
    def __init__(self):
        self.redis_host: str = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db: int = int(os.getenv('REDIS_DB', '0'))
        self.jwt_secret_key: str = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
        self.jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
        self.rate_limit_requests: int = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))
        self.rate_limit_window: int = int(os.getenv('RATE_LIMIT_WINDOW', '60'))  # seconds
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        self.model_version: str = 'VGG-Face'
        self.milvus_host: str = os.getenv('MILVUS_HOST', 'localhost')
        self.milvus_port: int = int(os.getenv('MILVUS_PORT', '19530'))
        self.collection_name: str = os.getenv('MILVUS_COLLECTION', 'face_embeddings')
        self.user_service_url: str = os.getenv('USER_SERVICE_URL', 'http://user-service:8001')

config = Config()