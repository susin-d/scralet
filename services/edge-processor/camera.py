import abc
import time
import cv2
import socket
import threading
from typing import Optional, Tuple, List, Dict
import structlog
import numpy as np

logger = structlog.get_logger()

class BaseCamera(abc.ABC):
    """Abstract base class for camera implementations."""

    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.connected = False
        self.last_frame_time = None

    @abc.abstractmethod
    def connect(self) -> bool:
        """Establish connection to the camera."""
        pass

    @abc.abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the camera."""
        pass

    @abc.abstractmethod
    def read_frame(self) -> Optional[np.ndarray]:
        """Read a single frame from the camera."""
        pass

    @abc.abstractmethod
    def is_connected(self) -> bool:
        """Check if camera is currently connected."""
        pass

    @abc.abstractmethod
    def reconnect(self) -> bool:
        """Attempt to reconnect to the camera."""
        pass

    def get_status(self) -> dict:
        """Get camera status information."""
        return {
            'camera_id': self.camera_id,
            'connected': self.connected,
            'last_frame_time': self.last_frame_time
        }


class CCTVCamera(BaseCamera):
    """CCTV network camera implementation supporting RTSP and HTTP streaming."""

    def __init__(self, camera_id: str, ip_address: str, port: int = 554,
                 protocol: str = "rtsp", username: Optional[str] = None,
                 password: Optional[str] = None, timeout: int = 10):
        super().__init__(camera_id)
        self.ip_address = ip_address
        self.port = port
        self.protocol = protocol.lower()  # rtsp or http
        self.username = username
        self.password = password
        self.timeout = timeout
        self.capture: Optional[cv2.VideoCapture] = None
        self.connection_lock = threading.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2  # seconds

    def _build_stream_url(self) -> str:
        """Build the stream URL based on protocol and authentication."""
        if self.protocol == "rtsp":
            base_url = f"rtsp://{self.ip_address}:{self.port}/live/ch0"
        elif self.protocol == "http":
            base_url = f"http://{self.ip_address}:{self.port}/video"
        else:
            raise ValueError(f"Unsupported protocol: {self.protocol}")

        if self.username and self.password:
            # Insert credentials into URL
            protocol_part = f"{self.protocol}://"
            auth_part = f"{self.username}:{self.password}@"
            url = base_url.replace(protocol_part, protocol_part + auth_part)
            return url
        return base_url

    def connect(self) -> bool:
        """Establish connection to the CCTV camera."""
        with self.connection_lock:
            try:
                if self.capture and self.capture.isOpened():
                    self.capture.release()

                stream_url = self._build_stream_url()
                logger.info("Attempting to connect to CCTV camera",
                          camera_id=self.camera_id, url=stream_url.replace(self.password or "", "***"))

                self.capture = cv2.VideoCapture(stream_url, cv2.CAP_FFMPEG)
                self.capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize buffer

                if not self.capture.isOpened():
                    logger.error("Failed to open video capture", camera_id=self.camera_id)
                    return False

                # Test reading a frame to verify connection
                ret, frame = self.capture.read()
                if not ret or frame is None:
                    logger.error("Failed to read initial frame", camera_id=self.camera_id)
                    self.capture.release()
                    return False

                self.connected = True
                self.last_frame_time = time.time()
                self.reconnect_attempts = 0
                logger.info("Successfully connected to CCTV camera", camera_id=self.camera_id)
                return True

            except Exception as e:
                logger.error("Error connecting to CCTV camera",
                           camera_id=self.camera_id, error=str(e))
                if self.capture:
                    self.capture.release()
                return False

    def disconnect(self) -> None:
        """Disconnect from the CCTV camera."""
        with self.connection_lock:
            if self.capture and self.capture.isOpened():
                self.capture.release()
                self.capture = None
            self.connected = False
            logger.info("Disconnected from CCTV camera", camera_id=self.camera_id)

    def read_frame(self) -> Optional[np.ndarray]:
        """Read a single frame from the CCTV camera."""
        if not self.is_connected():
            return None

        try:
            ret, frame = self.capture.read()
            if ret and frame is not None:
                self.last_frame_time = time.time()
                return frame
            else:
                logger.warning("Failed to read frame from CCTV camera", camera_id=self.camera_id)
                self.connected = False
                return None
        except Exception as e:
            logger.error("Error reading frame from CCTV camera",
                        camera_id=self.camera_id, error=str(e))
            self.connected = False
            return None

    def is_connected(self) -> bool:
        """Check if CCTV camera is currently connected."""
        if not self.capture or not self.capture.isOpened():
            self.connected = False
            return False

        # Additional check: try to grab a frame without retrieving it
        try:
            if not self.capture.grab():
                self.connected = False
                return False
        except Exception:
            self.connected = False
            return False

        return self.connected

    def reconnect(self) -> bool:
        """Attempt to reconnect to the CCTV camera with exponential backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached", camera_id=self.camera_id)
            return False

        self.reconnect_attempts += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_attempts - 1))
        logger.info("Attempting reconnection", camera_id=self.camera_id,
                   attempt=self.reconnect_attempts, delay=delay)

        time.sleep(delay)
        return self.connect()

    @staticmethod
    def discover_cameras(ip_range: str, ports: List[int] = None) -> List[Dict[str, str]]:
        """Discover CCTV cameras by scanning IP ranges."""
        if ports is None:
            ports = [554, 80, 8080]  # Common RTSP and HTTP ports

        discovered_cameras = []

        try:
            # Parse IP range (e.g., "192.168.1.0/24")
            if '/' in ip_range:
                import ipaddress
                network = ipaddress.ip_network(ip_range, strict=False)
                ips = [str(ip) for ip in network.hosts()]
            else:
                # Single IP
                ips = [ip_range]

            for ip in ips:
                for port in ports:
                    try:
                        # Quick TCP connection test
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(1)
                        result = sock.connect_ex((ip, port))
                        sock.close()

                        if result == 0:
                            # Port is open, assume it's a camera
                            camera_info = {
                                'ip_address': ip,
                                'port': str(port),
                                'protocol': 'rtsp' if port == 554 else 'http'
                            }
                            discovered_cameras.append(camera_info)
                            logger.info("Discovered potential camera", **camera_info)

                    except Exception as e:
                        logger.debug("Error checking port", ip=ip, port=port, error=str(e))
                        continue

        except Exception as e:
            logger.error("Error during camera discovery", error=str(e))

        return discovered_cameras

    def get_status(self) -> dict:
        """Get CCTV camera status information."""
        status = super().get_status()
        status.update({
            'ip_address': self.ip_address,
            'port': self.port,
            'protocol': self.protocol,
            'authenticated': bool(self.username and self.password),
            'reconnect_attempts': self.reconnect_attempts
        })
        return status