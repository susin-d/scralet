import os
from typing import Optional

class Config:
    def __init__(self):
        self.postgres_host: str = os.getenv('POSTGRES_HOST', 'localhost')
        self.postgres_port: int = int(os.getenv('POSTGRES_PORT', '5432'))
        self.postgres_db: str = os.getenv('POSTGRES_DB', 'user_service')
        self.postgres_user: str = os.getenv('POSTGRES_USER', 'user')
        self.postgres_password: str = os.getenv('POSTGRES_PASSWORD', 'password')
        self.database_url: str = f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

        self.milvus_host: str = os.getenv('MILVUS_HOST', 'localhost')
        self.milvus_port: int = int(os.getenv('MILVUS_PORT', '19530'))
        self.collection_name: str = os.getenv('MILVUS_COLLECTION', 'face_embeddings')

        self.face_recognition_url: str = os.getenv('FACE_RECOGNITION_URL', 'http://face-recognition:8000')

        self.jwt_secret_key: str = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
        self.jwt_algorithm: str = os.getenv('JWT_ALGORITHM', 'HS256')
        self.jwt_expiration_hours: int = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))

        self.email_smtp_server: str = os.getenv('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        self.email_smtp_port: int = int(os.getenv('EMAIL_SMTP_PORT', '587'))
        self.email_username: str = os.getenv('EMAIL_USERNAME', '')
        self.email_password: str = os.getenv('EMAIL_PASSWORD', '')

        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')

config = Config()