import os

class Config:
    def __init__(self):
        self.user_service_url: str = os.getenv('USER_SERVICE_URL', 'http://user-service:8001')
        self.edge_processor_url: str = os.getenv('EDGE_PROCESSOR_URL', 'http://edge-processor:8000')
        self.face_recognition_url: str = os.getenv('FACE_RECOGNITION_URL', 'http://face-recognition:8000')

        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')

config = Config()