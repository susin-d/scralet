import cv2
import base64
import json
import time
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import structlog
from mtcnn import MTCNN
from kafka import KafkaProducer
from kafka.errors import KafkaError
import numpy as np
from PIL import Image
import io
import json as json_lib
import asyncio
import threading
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from starlette.websockets import WebSocket, WebSocketDisconnect
import websockets
import httpx

from config import config
from camera_manager import CameraManager

# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

class SightingEvent:
    def __init__(self, camera_id: str, timestamp: str, face_crop_b64: str, person_bbox: Tuple[int, int, int, int]):
        self.camera_id = camera_id
        self.timestamp = timestamp
        self.face_crop_b64 = face_crop_b64
        self.person_bbox = person_bbox

    def to_dict(self):
        return {
            'camera_id': self.camera_id,
            'timestamp': self.timestamp,
            'face_crop_b64': self.face_crop_b64,
            'person_bbox': self.person_bbox
        }

class TrackedObject:
    def __init__(self, object_id: str, camera_id: str, bbox: Tuple[int, int, int, int], confidence: float, object_type: str = "person"):
        self.object_id = object_id
        self.camera_id = camera_id
        self.bbox = bbox
        self.confidence = confidence
        self.object_type = object_type
        self.last_seen = datetime.utcnow().isoformat()
        self.user_id = None  # User ID if identified
        self.identification_confidence = 0.0  # Confidence score for identification

    def to_dict(self):
        return {
            'object_id': self.object_id,
            'camera_id': self.camera_id,
            'bbox': self.bbox,
            'confidence': self.confidence,
            'object_type': self.object_type,
            'last_seen': self.last_seen,
            'user_id': self.user_id,
            'identification_confidence': self.identification_confidence
        }

class EdgeProcessor:
    def __init__(self):
        self.hog = cv2.HOGDescriptor()
        self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        self.mtcnn = MTCNN()
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            acks='all'
        )
        self.camera_manager = CameraManager(monitor_interval=config.camera_monitor_interval)
        self._initialize_cameras()
        self.tracked_objects: Dict[str, TrackedObject] = {}
        self.websocket_clients: List[WebSocket] = []
        self.object_id_counter = 0
        # Face recognition service URL
        self.face_recognition_url = config.face_recognition_url
        # Identity tracker service URL
        self.identity_tracker_url = config.identity_tracker_url
        logger.info("EdgeProcessor initialized", camera_id=config.camera_id, store_zone=config.store_zone)

    def _initialize_cameras(self):
        """Initialize cameras from configuration."""
        try:
            # Initialize Bluetooth cameras
            if config.bluetooth_cameras:
                camera_configs = json_lib.loads(config.bluetooth_cameras)
                for camera_config in camera_configs:
                    camera_id = camera_config.get('id')
                    address = camera_config.get('address')
                    port = camera_config.get('port', 1)

                    if camera_id and address:
                        success = self.camera_manager.add_bluetooth_camera(camera_id, address, port)
                        if success:
                            logger.info("Initialized Bluetooth camera", camera_id=camera_id, address=address)
                        else:
                            logger.error("Failed to initialize Bluetooth camera", camera_id=camera_id, address=address)
                    else:
                        logger.warning("Invalid Bluetooth camera configuration", config=camera_config)

            # Initialize CCTV cameras
            if config.cctv_cameras:
                cctv_configs = json_lib.loads(config.cctv_cameras)
                for camera_config in cctv_configs:
                    camera_id = camera_config.get('id')
                    ip_address = camera_config.get('ip_address')
                    port = camera_config.get('port', 554)
                    protocol = camera_config.get('protocol', 'rtsp')
                    username = camera_config.get('username')
                    password = camera_config.get('password')
                    timeout = camera_config.get('timeout', 10)

                    if camera_id and ip_address:
                        success = self.camera_manager.add_cctv_camera(
                            camera_id, ip_address, port, protocol, username, password, timeout
                        )
                        if success:
                            logger.info("Initialized CCTV camera", camera_id=camera_id, ip_address=ip_address)
                        else:
                            logger.error("Failed to initialize CCTV camera", camera_id=camera_id, ip_address=ip_address)
                    else:
                        logger.warning("Invalid CCTV camera configuration", config=camera_config)

        except json_lib.JSONDecodeError as e:
            logger.error("Failed to parse camera configuration", error=str(e))
        except Exception as e:
            logger.error("Error initializing cameras", error=str(e))

    def detect_people(self, frame: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Detect people using HOG descriptor."""
        try:
            boxes, weights = self.hog.detectMultiScale(frame, winStride=(8, 8), padding=(32, 32), scale=1.05)
            return [(x, y, x + w, y + h) for (x, y, w, h) in boxes]
        except Exception as e:
            logger.error("Error in person detection", error=str(e))
            return []

    def detect_faces(self, frame: np.ndarray) -> List[dict]:
        """Detect faces using MTCNN."""
        try:
            return self.mtcnn.detect_faces(frame)
        except Exception as e:
            logger.error("Error in face detection", error=str(e))
            return []

    def crop_face(self, frame: np.ndarray, face: dict) -> Optional[np.ndarray]:
        """Crop face from frame based on detection result."""
        try:
            x, y, w, h = face['box']
            x, y = max(0, x), max(0, y)
            cropped = frame[y:y+h, x:x+w]
            return cropped if cropped.size > 0 else None
        except Exception as e:
            logger.error("Error cropping face", error=str(e))
            return None

    def encode_image_to_base64(self, image: np.ndarray) -> str:
        """Encode image to base64 string."""
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error("Error encoding image to base64", error=str(e))
            return ""

    async def recognize_face(self, face_image_b64: str) -> Optional[Dict]:
        """Call face recognition service to identify the person."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.face_recognition_url}/recognize",
                    json={"face_image_b64": face_image_b64}
                )
                response.raise_for_status()
                data = response.json()
                if data.get('tracked_objects'):
                    # Return the best match (highest confidence)
                    return max(data['tracked_objects'], key=lambda x: x['confidence'])
                return None
        except Exception as e:
            logger.error("Error calling face recognition service", error=str(e))
            return None

    async def get_user_face_data(self, user_id: str) -> Optional[Dict]:
        """Get user face data from face recognition service."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.face_recognition_url}/users/{user_id}/face")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error("Error getting user face data", user_id=user_id, error=str(e))
            return None

    def send_to_kafka(self, event: SightingEvent):
        """Send SightingEvent to Kafka with retries."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                event_data = event.to_dict()
                # Add additional camera metadata if available
                if hasattr(self, 'camera_manager') and event.camera_id != config.camera_id:
                    camera = self.camera_manager.get_camera(event.camera_id)
                    if camera:
                        camera_status = camera.get_status()
                        event_data['camera_metadata'] = {
                            'type': camera.__class__.__name__,
                            'connected': camera_status.get('connected', False),
                            'last_frame_time': camera_status.get('last_frame_time'),
                            'ip_address': camera_status.get('ip_address'),
                            'protocol': camera_status.get('protocol')
                        }

                future = self.producer.send(config.kafka_topic, event_data)
                record_metadata = future.get(timeout=10)
                logger.info("Event sent to Kafka", topic=record_metadata.topic, partition=record_metadata.partition, offset=record_metadata.offset, camera_id=event.camera_id)
                return
            except Exception as e:
                logger.warning("Failed to send event to Kafka", attempt=attempt + 1, error=str(e), camera_id=event.camera_id, exc_info=True)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        logger.error("Failed to send event to Kafka after all retries, event lost", camera_id=event.camera_id)

    async def process_frame(self, frame: np.ndarray, camera_id: str = None):
        """Process a single frame: detect people, then faces, create events and track objects."""
        try:
            people_boxes = self.detect_people(frame)
            logger.debug("People detected", count=len(people_boxes), camera_id=camera_id or config.camera_id)

            current_objects = {}
            for person_box in people_boxes:
                # Generate object ID (simple tracking - in production use proper tracking algorithm)
                object_id = f"{camera_id or config.camera_id}_{self.object_id_counter}"
                self.object_id_counter += 1

                # Create tracked object
                tracked_obj = TrackedObject(object_id, camera_id or config.camera_id, person_box, 0.8)
                current_objects[object_id] = tracked_obj

                # Crop person region for face detection
                x1, y1, x2, y2 = person_box
                person_region = frame[y1:y2, x1:x2]

                if person_region.size == 0:
                    continue

                faces = self.detect_faces(person_region)
                logger.debug("Faces detected in person region", count=len(faces), camera_id=camera_id or config.camera_id)

                for face in faces:
                    cropped_face = self.crop_face(person_region, face)
                    if cropped_face is not None:
                        face_crop_b64 = self.encode_image_to_base64(cropped_face)
                        if face_crop_b64:
                            # Recognize face using face recognition service
                            recognition_result = await self.recognize_face(face_crop_b64)
                            user_id = None
                            identification_confidence = 0.0
                            if recognition_result:
                                user_id = recognition_result.get('id')
                                identification_confidence = recognition_result.get('confidence', 0.0)
                                logger.info("Face recognized", user_id=user_id, confidence=identification_confidence, camera_id=camera_id or config.camera_id)

                            # Update tracked object with user identification
                            tracked_obj.user_id = user_id
                            tracked_obj.identification_confidence = identification_confidence

                            timestamp = datetime.utcnow().isoformat()
                            event = SightingEvent(camera_id or config.camera_id, timestamp, face_crop_b64, person_box)
                            self.send_to_kafka(event)
                            logger.info("Sighting event created and sent", camera_id=camera_id or config.camera_id, user_id=user_id)

            # Update tracked objects
            self.update_tracked_objects(current_objects, camera_id or config.camera_id)

        except Exception as e:
            logger.error("Error processing frame", error=str(e), camera_id=camera_id or config.camera_id)

    def update_tracked_objects(self, current_objects: Dict[str, TrackedObject], camera_id: str):
        """Update tracked objects and notify WebSocket clients."""
        # Remove objects not seen in this frame (simple cleanup)
        to_remove = [obj_id for obj_id, obj in self.tracked_objects.items()
                    if obj.camera_id == camera_id and obj_id not in current_objects]
        for obj_id in to_remove:
            del self.tracked_objects[obj_id]

        # Add new objects
        for obj_id, obj in current_objects.items():
            self.tracked_objects[obj_id] = obj

        # Broadcast updates to WebSocket clients
        self.broadcast_tracking_updates(camera_id)

    def broadcast_tracking_updates(self, camera_id: str):
        """Broadcast tracking updates to all connected WebSocket clients."""
        updates = [obj.to_dict() for obj in self.tracked_objects.values() if obj.camera_id == camera_id]
        message = {
            'type': 'tracking_update',
            'camera_id': camera_id,
            'objects': updates,
            'timestamp': datetime.utcnow().isoformat()
        }

        # Send to all connected clients
        for client in self.websocket_clients[:]:  # Copy list to avoid modification during iteration
            try:
                asyncio.run(client.send_json(message))
            except Exception as e:
                logger.warning("Failed to send tracking update to client", error=str(e))
                try:
                    self.websocket_clients.remove(client)
                except ValueError:
                    pass

    def process_all_cameras(self):
        """Main loop to process video frames from managed cameras."""
        # Start camera monitoring
        self.camera_manager.start_monitoring()

        # For backward compatibility, also support direct video source if no cameras are configured
        cameras = self.camera_manager.get_all_cameras()
        if not cameras:
            logger.warning("No cameras configured, falling back to direct video source")
            cap = cv2.VideoCapture(config.video_source)
            if not cap.isOpened():
                logger.error("Could not open video source", source=config.video_source)
                return

            logger.info("Starting video processing with direct source", source=config.video_source)

            try:
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        logger.info("End of video reached, restarting")
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Loop back to beginning
                        continue

                    # Create event loop for async processing
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.process_frame(frame))
                    loop.close()
                    time.sleep(0.1)  # Small delay to prevent overwhelming the system

            except KeyboardInterrupt:
                logger.info("Processing interrupted by user")
            except Exception as e:
                logger.error("Unexpected error during processing", error=str(e), exc_info=True)
            finally:
                cap.release()
        else:
            logger.info("Starting multi-camera processing", camera_count=len(cameras))

            try:
                while True:
                    for camera in cameras:
                        if camera.is_connected():
                            frame = camera.read_frame()
                            if frame is not None:
                                # Create event loop for async processing
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(self.process_frame(frame, camera.camera_id))
                                loop.close()
                            else:
                                logger.debug("No frame available from camera", camera_id=camera.camera_id)
                        else:
                            logger.warning("Camera not connected, skipping", camera_id=camera.camera_id)

                    # Periodic health check and status logging
                    if int(time.time()) % 60 == 0:  # Every minute
                        status_summary = self.camera_manager.get_status_summary()
                        logger.info("Camera status summary", **status_summary)

                    time.sleep(0.1)  # Small delay to prevent overwhelming the system

            except KeyboardInterrupt:
                logger.info("Processing interrupted by user")
            except Exception as e:
                logger.error("Unexpected error during multi-camera processing", error=str(e), exc_info=True)

        # Cleanup
        self.camera_manager.stop_monitoring()
        self.producer.close()
        logger.info("Multi-camera processing stopped")

    def get_camera_stream_url(self, camera_id: str) -> str:
        """Get the stream URL for a specific camera."""
        camera = self.camera_manager.get_camera(camera_id)
        if not camera:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

        if hasattr(camera, 'ip_address'):
            # CCTV camera
            return f"{camera.protocol}://{camera.ip_address}:{camera.port}/stream"
        else:
            # Bluetooth or other camera types - return generic stream endpoint
            return f"/cameras/{camera_id}/stream"

    def get_camera_tracking_data(self, camera_id: str) -> List[Dict]:
        """Get current tracking data for a specific camera."""
        return [obj.to_dict() for obj in self.tracked_objects.values() if obj.camera_id == camera_id]

    def generate_stream_frames(self, camera_id: str):
        """Generator for streaming camera frames."""
        camera = self.camera_manager.get_camera(camera_id)
        if not camera:
            return

        while True:
            if camera.is_connected():
                frame = camera.read_frame()
                if frame is not None:
                    # Encode frame as JPEG
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                else:
                    time.sleep(0.1)
            else:
                time.sleep(1)  # Wait before retrying

# FastAPI app
app = FastAPI(title="Edge Processor API", version="1.0.0")

# Global processor instance
processor = None

@app.on_event("startup")
async def startup_event():
    global processor
    processor = EdgeProcessor()
    # Start processing in background thread
    thread = threading.Thread(target=processor.process_all_cameras, daemon=True)
    thread.start()

@app.get("/cameras/{camera_id}/stream")
async def get_camera_stream(camera_id: str):
    """Get live video stream for a camera."""
    if not processor:
        raise HTTPException(status_code=503, detail="Service not ready")

    camera = processor.camera_manager.get_camera(camera_id)
    if not camera:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    return StreamingResponse(
        processor.generate_stream_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/cameras/{camera_id}/tracking")
async def get_camera_tracking(camera_id: str):
    """Get current tracking data for a camera."""
    if not processor:
        raise HTTPException(status_code=503, detail="Service not ready")

    tracking_data = processor.get_camera_tracking_data(camera_id)
    return {"camera_id": camera_id, "tracked_objects": tracking_data}

@app.websocket("/ws/tracking")
async def websocket_tracking(websocket: WebSocket):
    """WebSocket endpoint for live tracking updates."""
    await websocket.accept()
    if processor:
        processor.websocket_clients.append(websocket)

    try:
        while True:
            # Keep connection alive, updates are pushed from processor
            await websocket.receive_text()
    except WebSocketDisconnect:
        if processor:
            try:
                processor.websocket_clients.remove(websocket)
            except ValueError:
                pass

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)