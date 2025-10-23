import os
from typing import Optional

class Config:
    def __init__(self):
        self.camera_id: str = os.getenv('CAMERA_ID', 'default_camera')
        self.store_zone: str = os.getenv('STORE_ZONE', 'default_zone')
        self.kafka_bootstrap_servers: str = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        self.kafka_topic: str = os.getenv('KAFKA_TOPIC', 'camera-sighting-events')
        self.video_source: str = os.getenv('VIDEO_SOURCE', 'test_video.mp4')
        self.log_level: str = os.getenv('LOG_LEVEL', 'INFO')
        # Bluetooth camera configuration
        self.bluetooth_cameras: str = os.getenv('BLUETOOTH_CAMERAS', '')  # JSON string of camera configs
        self.bluetooth_discovery_duration: int = int(os.getenv('BLUETOOTH_DISCOVERY_DURATION', '8'))

        # CCTV camera configuration
        self.cctv_cameras: str = os.getenv('CCTV_CAMERAS', '')  # JSON string of CCTV camera configs
        self.cctv_discovery_ip_range: str = os.getenv('CCTV_DISCOVERY_IP_RANGE', '192.168.1.0/24')
        self.cctv_discovery_ports: str = os.getenv('CCTV_DISCOVERY_PORTS', '554,80,8080')  # Comma-separated ports

        # General camera monitoring
        self.camera_monitor_interval: int = int(os.getenv('CAMERA_MONITOR_INTERVAL', '10'))

        # Service URLs for face recognition and identity tracking
        self.face_recognition_url: str = os.getenv('FACE_RECOGNITION_URL', 'http://face-recognition:8000')
        self.identity_tracker_url: str = os.getenv('IDENTITY_TRACKER_URL', 'http://identity-tracker:8001')
        self.user_service_url: str = os.getenv('USER_SERVICE_URL', 'http://user-service:8001')

config = Config()