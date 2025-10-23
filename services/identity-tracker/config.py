import os
from typing import Optional

class Config:
    def __init__(self):
        self.kafka_bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_consumer_topic: str = os.getenv('KAFKA_CONSUMER_TOPIC', 'camera-sighting-events')
        self.kafka_producer_topic: str = os.getenv('KAFKA_PRODUCER_TOPIC', 'customer-identified')
        self.redis_host: str = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db: int = int(os.getenv('REDIS_DB', '0'))
        self.face_recognition_url: str = os.getenv('FACE_RECOGNITION_URL', 'http://face-recognition:8000')
        self.milvus_host: str = os.getenv('MILVUS_HOST', 'localhost')
        self.milvus_port: int = int(os.getenv('MILVUS_PORT', '19530'))
        self.collection_name: str = os.getenv('MILVUS_COLLECTION', 'face_embeddings')
        self.confidence_threshold: float = float(os.getenv('CONFIDENCE_THRESHOLD', '95.0'))
        self.session_timeout: int = int(os.getenv('SESSION_TIMEOUT', '300'))  # seconds
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        self.service_port: int = int(os.getenv('SERVICE_PORT', '8001'))
        self.tracking_timeout: int = int(os.getenv('TRACKING_TIMEOUT', '3600'))  # 1 hour for person tracking

config = Config()