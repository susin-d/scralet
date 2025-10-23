import time
import threading
from typing import Optional, List, Dict
import structlog
import numpy as np
import cv2
import bluetooth

from camera import BaseCamera

logger = structlog.get_logger()

class BluetoothCamera(BaseCamera):
    """Bluetooth camera implementation using pybluez."""

    def __init__(self, camera_id: str, device_address: str, port: int = 1, reconnect_attempts: int = 3):
        super().__init__(camera_id)
        self.device_address = device_address
        self.port = port
        self.reconnect_attempts = reconnect_attempts
        self.socket: Optional[bluetooth.BluetoothSocket] = None
        self.stream_thread: Optional[threading.Thread] = None
        self.stop_stream = False
        self.frame_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 10  # Keep last 10 frames

    def discover_devices(self, duration: int = 8) -> List[Dict[str, str]]:
        """Discover nearby Bluetooth devices."""
        try:
            logger.info("Starting Bluetooth device discovery", duration=duration)
            nearby_devices = bluetooth.discover_devices(duration=duration, lookup_names=True, flush_cache=True)
            devices = []
            for addr, name in nearby_devices:
                devices.append({'address': addr, 'name': name})
                logger.info("Found Bluetooth device", address=addr, name=name)
            return devices
        except Exception as e:
            logger.error("Error during Bluetooth device discovery", error=str(e))
            return []

    def connect(self) -> bool:
        """Establish Bluetooth connection to camera."""
        for attempt in range(self.reconnect_attempts):
            try:
                logger.info("Attempting to connect to Bluetooth camera", camera_id=self.camera_id,
                           address=self.device_address, attempt=attempt + 1)

                self.socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                self.socket.connect((self.device_address, self.port))
                self.connected = True

                # Start video streaming thread
                self.stop_stream = False
                self.stream_thread = threading.Thread(target=self._stream_video, daemon=True)
                self.stream_thread.start()

                logger.info("Successfully connected to Bluetooth camera", camera_id=self.camera_id)
                return True

            except Exception as e:
                logger.warning("Failed to connect to Bluetooth camera", camera_id=self.camera_id,
                              attempt=attempt + 1, error=str(e))
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                self.socket = None

                if attempt < self.reconnect_attempts - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

        logger.error("Failed to connect to Bluetooth camera after all attempts", camera_id=self.camera_id)
        return False

    def disconnect(self) -> None:
        """Disconnect from Bluetooth camera."""
        logger.info("Disconnecting from Bluetooth camera", camera_id=self.camera_id)
        self.stop_stream = True

        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=5)

        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.warning("Error closing Bluetooth socket", error=str(e))

        self.socket = None
        self.connected = False
        logger.info("Disconnected from Bluetooth camera", camera_id=self.camera_id)

    def _stream_video(self) -> None:
        """Background thread to receive video stream from Bluetooth camera."""
        try:
            while not self.stop_stream and self.socket:
                try:
                    # Receive frame data (assuming JPEG frames with size prefix)
                    size_data = self.socket.recv(4)
                    if len(size_data) != 4:
                        break

                    frame_size = int.from_bytes(size_data, byteorder='big')
                    frame_data = b''

                    while len(frame_data) < frame_size:
                        chunk = self.socket.recv(min(4096, frame_size - len(frame_data)))
                        if not chunk:
                            break
                        frame_data += chunk

                    if len(frame_data) == frame_size:
                        # Decode JPEG frame
                        frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if frame is not None:
                            with self.buffer_lock:
                                self.frame_buffer.append(frame)
                                if len(self.frame_buffer) > self.max_buffer_size:
                                    self.frame_buffer.pop(0)
                            self.last_frame_time = time.time()

                except Exception as e:
                    logger.error("Error receiving frame from Bluetooth camera", camera_id=self.camera_id, error=str(e))
                    break

        except Exception as e:
            logger.error("Error in video streaming thread", camera_id=self.camera_id, error=str(e))
        finally:
            self.connected = False
            logger.info("Video streaming thread stopped", camera_id=self.camera_id)

    def read_frame(self) -> Optional[np.ndarray]:
        """Read the latest frame from the buffer."""
        with self.buffer_lock:
            if self.frame_buffer:
                return self.frame_buffer[-1].copy()
        return None

    def is_connected(self) -> bool:
        """Check if camera is connected and streaming."""
        return self.connected and self.socket is not None and self.stream_thread and self.stream_thread.is_alive()

    def reconnect(self) -> bool:
        """Attempt to reconnect to the camera."""
        logger.info("Attempting to reconnect to Bluetooth camera", camera_id=self.camera_id)
        self.disconnect()
        time.sleep(1)  # Brief pause before reconnecting
        return self.connect()