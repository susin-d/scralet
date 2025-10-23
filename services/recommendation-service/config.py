import os
from typing import Optional

class Config:
    def __init__(self):
        self.kafka_bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_consumer_topic: str = os.getenv('KAFKA_CONSUMER_TOPIC', 'customer-identified')
        self.kafka_producer_topic: str = os.getenv('KAFKA_PRODUCER_TOPIC', 'action-events')
        self.redis_host: str = os.getenv('REDIS_HOST', 'localhost')
        self.redis_port: int = int(os.getenv('REDIS_PORT', '6379'))
        self.redis_db: int = int(os.getenv('REDIS_DB', '0'))
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')

config = Config()