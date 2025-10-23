import os
from typing import Optional

class Config:
    def __init__(self):
        self.kafka_bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic: str = os.getenv('KAFKA_TOPIC', 'action-events')
        self.signage_api_url: str = os.getenv('SIGNAGE_API_URL', 'http://localhost:8080/api/display')
        self.store_zone: str = os.getenv('STORE_ZONE', 'default_zone')
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        self.user_service_url: str = os.getenv('USER_SERVICE_URL', 'http://user-service:8001')
        self.face_recognition_url: str = os.getenv('FACE_RECOGNITION_URL', 'http://face-recognition:8000')

config = Config()