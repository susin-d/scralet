import time
import threading
from typing import List, Dict, Optional
import structlog

from camera import BaseCamera, CCTVCamera
from bluetooth_camera import BluetoothCamera

logger = structlog.get_logger()

class CameraManager:
    """Manages multiple cameras and handles discovery, connection, and monitoring."""

    def __init__(self, discovery_interval: int = 30, monitor_interval: int = 10):
        self.cameras: Dict[str, BaseCamera] = {}
        self.discovery_interval = discovery_interval
        self.monitor_interval = monitor_interval
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = False

    def discover_bluetooth_cameras(self) -> List[Dict[str, str]]:
        """Discover available Bluetooth cameras."""
        # Create a temporary camera instance for discovery
        temp_camera = BluetoothCamera("temp", "00:00:00:00:00:00")
        devices = temp_camera.discover_devices()
        return devices

    def discover_cctv_cameras(self, ip_range: str, ports: List[int] = None) -> List[Dict[str, str]]:
        """Discover available CCTV cameras by scanning IP ranges."""
        return CCTVCamera.discover_cameras(ip_range, ports)

    def add_bluetooth_camera(self, camera_id: str, device_address: str, port: int = 1) -> bool:
        """Add a Bluetooth camera to the manager."""
        if camera_id in self.cameras:
            logger.warning("Camera already exists", camera_id=camera_id)
            return False

        camera = BluetoothCamera(camera_id, device_address, port)
        self.cameras[camera_id] = camera

        if camera.connect():
            logger.info("Successfully added and connected Bluetooth camera", camera_id=camera_id)
            return True
        else:
            logger.error("Failed to connect Bluetooth camera", camera_id=camera_id)
            return False

    def add_cctv_camera(self, camera_id: str, ip_address: str, port: int = 554,
                        protocol: str = "rtsp", username: Optional[str] = None,
                        password: Optional[str] = None, timeout: int = 10) -> bool:
        """Add a CCTV camera to the manager."""
        if camera_id in self.cameras:
            logger.warning("Camera already exists", camera_id=camera_id)
            return False

        camera = CCTVCamera(camera_id, ip_address, port, protocol, username, password, timeout)
        self.cameras[camera_id] = camera

        if camera.connect():
            logger.info("Successfully added and connected CCTV camera", camera_id=camera_id)
            return True
        else:
            logger.error("Failed to connect CCTV camera", camera_id=camera_id)
            return False

    def remove_camera(self, camera_id: str) -> None:
        """Remove a camera from the manager."""
        if camera_id in self.cameras:
            self.cameras[camera_id].disconnect()
            del self.cameras[camera_id]
            logger.info("Removed camera", camera_id=camera_id)

    def get_camera(self, camera_id: str) -> Optional[BaseCamera]:
        """Get a camera by ID."""
        return self.cameras.get(camera_id)

    def get_all_cameras(self) -> List[BaseCamera]:
        """Get all managed cameras."""
        return list(self.cameras.values())

    def start_monitoring(self) -> None:
        """Start the monitoring thread."""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Monitoring already running")
            return

        self.stop_monitoring = False
        self.monitor_thread = threading.Thread(target=self._monitor_cameras, daemon=True)
        self.monitor_thread.start()
        logger.info("Started camera monitoring")

    def stop_monitoring(self) -> None:
        """Stop the monitoring thread."""
        self.stop_monitoring = True
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Stopped camera monitoring")

    def _monitor_cameras(self) -> None:
        """Background thread to monitor camera connections and reconnect if needed."""
        while not self.stop_monitoring:
            try:
                for camera_id, camera in list(self.cameras.items()):
                    if not camera.is_connected():
                        logger.warning("Camera disconnected, attempting reconnection", camera_id=camera_id)
                        if not camera.reconnect():
                            logger.error("Failed to reconnect camera", camera_id=camera_id)
                    else:
                        # Log status periodically
                        status = camera.get_status()
                        logger.debug("Camera status", **status)

                time.sleep(self.monitor_interval)

            except Exception as e:
                logger.error("Error in camera monitoring", error=str(e))
                time.sleep(self.monitor_interval)

    def get_status_summary(self) -> Dict[str, any]:
        """Get a summary of all camera statuses."""
        summary = {
            'total_cameras': len(self.cameras),
            'connected_cameras': 0,
            'disconnected_cameras': 0,
            'camera_details': []
        }

        for camera_id, camera in self.cameras.items():
            status = camera.get_status()
            summary['camera_details'].append(status)
            if status['connected']:
                summary['connected_cameras'] += 1
            else:
                summary['disconnected_cameras'] += 1

        return summary