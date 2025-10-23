import json
import time
import uuid
from typing import List, Dict, Any, Optional
import structlog
import redis
import requests
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError
from pymilvus import connections, Collection
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import asyncio
from datetime import datetime

from config import config

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

# Pydantic models for API
class TrackedObject(BaseModel):
    person_id: str
    camera_id: str
    timestamp: str
    position: Dict[str, float]  # x, y coordinates
    confidence: float
    customer_id: Optional[str] = None

class TrackingUpdate(BaseModel):
    camera_id: str
    timestamp: str
    objects: List[TrackedObject]

class PersonData(BaseModel):
    person_id: str
    customer_id: Optional[str] = None
    first_seen: str
    last_seen: str
    cameras: List[str]
    positions: List[Dict[str, Any]]

class IdentifiedCustomerEvent:
    def __init__(self, customer_id: str, confidence: float, camera_id: str, timestamp: str):
        self.customer_id = customer_id
        self.confidence = confidence
        self.camera_id = camera_id
        self.timestamp = timestamp

    def to_dict(self):
        return {
            'customer_id': self.customer_id,
            'confidence': self.confidence,
            'camera_id': self.camera_id,
            'timestamp': self.timestamp
        }

class IdentityTracker:
    def __init__(self):
        # Redis for session tracking and person tracking
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True
        )

        # Kafka consumer for camera-sighting-events
        self.consumer = KafkaConsumer(
            config.kafka_consumer_topic,
            bootstrap_servers=config.kafka_bootstrap_servers,
            group_id='identity-tracker-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )

        # Kafka producer for customer-identified events
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            acks='all'
        )

        # Milvus connection
        try:
            connections.connect("default", host=config.milvus_host, port=config.milvus_port)
            self.collection = Collection(config.collection_name)
            self.collection.load()
        except Exception as e:
            logger.warning("Failed to connect to Milvus, face recognition will use fallback", error=str(e))
            self.collection = None

        # WebSocket clients for real-time tracking updates
        self.websocket_clients: List[WebSocket] = []

        logger.info("IdentityTracker initialized")

    def get_face_embedding(self, face_image_b64: str) -> List[float]:
        """Call face-recognition service to get embedding."""
        try:
            response = requests.post(
                f"{config.face_recognition_url}/generate-embedding",
                json={"face_image_b64": face_image_b64},
                timeout=10
            )
            response.raise_for_status()
            return response.json()['embedding']
        except Exception as e:
            logger.error("Failed to get face embedding, using fallback", error=str(e))
            # Fallback: return a dummy embedding that won't match anything
            return [0.0] * 512

    def search_similar_faces(self, embedding: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Query Milvus for nearest neighbors."""
        if self.collection is None:
            logger.warning("Milvus collection not available, using fallback")
            return []

        try:
            search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
            results = self.collection.search(
                [embedding], "embedding", search_params, limit=top_k, output_fields=["customer_id"]
            )
            return [
                {"customer_id": hit.entity.get('customer_id'), "distance": hit.distance}
                for hit in results[0]
            ]
        except Exception as e:
            logger.error("Failed to search similar faces in Milvus, using fallback", error=str(e))
            # Fallback: return empty list, no matches
            return []

    def update_session_confidence(self, session_id: str, customer_id: str, distance: float):
        """Update confidence score in Redis session."""
        try:
            # Convert distance to confidence (lower distance = higher confidence)
            confidence = max(0, 100 - (distance * 100))  # Assuming distance is normalized

            session_key = f"session:{session_id}"
            customer_key = f"{session_key}:{customer_id}"

            # Get current confidence
            current_confidence = float(self.redis_client.get(customer_key) or 0)

            # Update with higher confidence if better
            if confidence > current_confidence:
                self.redis_client.set(customer_key, confidence)
                self.redis_client.expire(customer_key, config.session_timeout)

            # Set session expiration
            self.redis_client.expire(session_key, config.session_timeout)
        except Exception as e:
            logger.error("Failed to update session confidence in Redis, skipping", error=str(e))

    def check_identification_threshold(self, session_id: str) -> IdentifiedCustomerEvent:
        """Check if any customer in session exceeds confidence threshold."""
        try:
            session_key = f"session:{session_id}"
            keys = self.redis_client.keys(f"{session_key}:*")

            for key in keys:
                confidence = float(self.redis_client.get(key) or 0)
                if confidence > config.confidence_threshold:
                    customer_id = key.split(':')[-1]
                    # Get session metadata (assuming stored separately)
                    metadata = self.redis_client.hgetall(session_key)
                    return IdentifiedCustomerEvent(
                        customer_id=customer_id,
                        confidence=confidence,
                        camera_id=metadata.get('camera_id', 'unknown'),
                        timestamp=metadata.get('timestamp', time.time())
                    )
            return None
        except Exception as e:
            logger.error("Failed to check identification threshold in Redis, returning None", error=str(e))
            return None

    def publish_identified_event(self, event: IdentifiedCustomerEvent):
        """Publish IdentifiedCustomerEvent to Kafka."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                future = self.producer.send(config.kafka_producer_topic, event.to_dict())
                record_metadata = future.get(timeout=10)
                logger.info("Identified event published",
                            topic=record_metadata.topic,
                            customer_id=event.customer_id,
                            confidence=event.confidence)
                return
            except Exception as e:
                logger.warning("Failed to publish identified event to Kafka", attempt=attempt + 1, error=str(e))
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        logger.error("Failed to publish identified event to Kafka after all retries, event lost")

    def delete_session(self, session_id: str):
        """Delete session from Redis after identification."""
        try:
            session_key = f"session:{session_id}"
            keys = self.redis_client.keys(f"{session_key}:*")
            keys.append(session_key)
            self.redis_client.delete(*keys)
            logger.info("Session deleted", session_id=session_id)
        except Exception as e:
            logger.error("Failed to delete session from Redis", error=str(e))

    def assign_person_id(self, camera_id: str, timestamp: str, position: Dict[str, float]) -> str:
        """Assign a persistent person ID based on position and time proximity."""
        try:
            # Check for existing persons in nearby positions within time window
            current_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            time_window = 30  # seconds

            # Search for recent person positions
            person_keys = self.redis_client.keys("person:*:positions")
            for key in person_keys:
                person_id = key.split(":")[1]
                positions = self.redis_client.lrange(key, -10, -1)  # Last 10 positions

                for pos_str in positions:
                    pos_data = json.loads(pos_str)
                    pos_time = datetime.fromisoformat(pos_data['timestamp'].replace('Z', '+00:00'))
                    time_diff = abs((current_time - pos_time).total_seconds())

                    if time_diff <= time_window:
                        # Check spatial proximity (simple Euclidean distance)
                        dx = position.get('x', 0) - pos_data['position'].get('x', 0)
                        dy = position.get('y', 0) - pos_data['position'].get('y', 0)
                        distance = (dx**2 + dy**2)**0.5

                        if distance <= 50:  # pixels threshold
                            return person_id

            # No matching person found, create new ID
            person_id = str(uuid.uuid4())
            logger.info("New person assigned", person_id=person_id, camera_id=camera_id)
            return person_id

        except Exception as e:
            logger.error("Failed to assign person ID", error=str(e))
            return str(uuid.uuid4())

    def update_person_tracking(self, person_id: str, camera_id: str, timestamp: str, position: Dict[str, float], customer_id: Optional[str] = None):
        """Update tracking data for a person in Redis."""
        try:
            # Update person metadata
            person_key = f"person:{person_id}"
            person_data = self.redis_client.hgetall(person_key)

            if not person_data:
                # New person
                person_data = {
                    'first_seen': timestamp,
                    'customer_id': customer_id or '',
                    'cameras': json.dumps([camera_id])
                }
            else:
                # Existing person
                cameras = json.loads(person_data.get('cameras', '[]'))
                if camera_id not in cameras:
                    cameras.append(camera_id)
                person_data['cameras'] = json.dumps(cameras)
                if customer_id and not person_data.get('customer_id'):
                    person_data['customer_id'] = customer_id

            person_data['last_seen'] = timestamp
            self.redis_client.hset(person_key, mapping=person_data)
            self.redis_client.expire(person_key, config.tracking_timeout)

            # Add position to history
            position_key = f"person:{person_id}:positions"
            position_data = {
                'timestamp': timestamp,
                'camera_id': camera_id,
                'position': position
            }
            self.redis_client.rpush(position_key, json.dumps(position_data))
            self.redis_client.expire(position_key, config.tracking_timeout)

            # Keep only last 100 positions
            self.redis_client.ltrim(position_key, -100, -1)

            logger.debug("Person tracking updated", person_id=person_id, camera_id=camera_id)

        except Exception as e:
            logger.error("Failed to update person tracking", person_id=person_id, error=str(e))

    def get_person_data(self, person_id: str) -> Optional[PersonData]:
        """Retrieve person tracking data."""
        try:
            person_key = f"person:{person_id}"
            person_data = self.redis_client.hgetall(person_key)

            if not person_data:
                return None

            position_key = f"person:{person_id}:positions"
            positions = [json.loads(pos) for pos in self.redis_client.lrange(position_key, 0, -1)]

            return PersonData(
                person_id=person_id,
                customer_id=person_data.get('customer_id') or None,
                first_seen=person_data['first_seen'],
                last_seen=person_data['last_seen'],
                cameras=json.loads(person_data['cameras']),
                positions=positions
            )

        except Exception as e:
            logger.error("Failed to get person data", person_id=person_id, error=str(e))
            return None

    async def broadcast_tracking_update(self, update: TrackingUpdate):
        """Broadcast tracking updates to WebSocket clients."""
        message = {
            "type": "tracking_update",
            "data": update.dict(),
            "timestamp": datetime.utcnow().isoformat()
        }

        disconnected_clients = []
        for client in self.websocket_clients[:]:
            try:
                await client.send_json(message)
            except Exception as e:
                logger.warning("Failed to send tracking update to client", error=str(e))
                disconnected_clients.append(client)

        # Clean up disconnected clients
        for client in disconnected_clients:
            if client in self.websocket_clients:
                self.websocket_clients.remove(client)

    def process_sighting_event(self, event: Dict[str, Any]):
        """Process a single camera sighting event."""
        try:
            camera_id = event['camera_id']
            timestamp = event['timestamp']
            face_crop_b64 = event['face_crop_b64']
            position = event.get('position', {'x': 0.0, 'y': 0.0})  # Default position if not provided

            # Generate session ID (could be based on camera and time window)
            session_id = f"{camera_id}_{int(time.time()) // 60}"  # Per minute session

            # Store session metadata
            session_key = f"session:{session_id}"
            self.redis_client.hset(session_key, mapping={
                'camera_id': camera_id,
                'timestamp': timestamp
            })
            self.redis_client.expire(session_key, config.session_timeout)

            # Assign or get existing person ID
            person_id = self.assign_person_id(camera_id, timestamp, position)

            # Get face embedding
            embedding = self.get_face_embedding(face_crop_b64)

            # Search for similar faces
            similar_faces = self.search_similar_faces(embedding)

            # Update confidence for each match
            for face in similar_faces:
                self.update_session_confidence(session_id, face['customer_id'], face['distance'])

            # Check for identification
            identified_event = self.check_identification_threshold(session_id)
            customer_id = identified_event.customer_id if identified_event else None

            # Update person tracking
            self.update_person_tracking(person_id, camera_id, timestamp, position, customer_id)

            # Create tracked object for broadcasting
            tracked_object = TrackedObject(
                person_id=person_id,
                camera_id=camera_id,
                timestamp=timestamp,
                position=position,
                confidence=identified_event.confidence if identified_event else 0.0,
                customer_id=customer_id
            )

            # Broadcast tracking update
            tracking_update = TrackingUpdate(
                camera_id=camera_id,
                timestamp=timestamp,
                objects=[tracked_object]
            )
            asyncio.create_task(self.broadcast_tracking_update(tracking_update))

            if identified_event:
                self.publish_identified_event(identified_event)
                self.delete_session(session_id)

        except Exception as e:
            logger.error("Error processing sighting event", error=str(e), event=event)

    def run(self):
        """Main loop to consume Kafka messages."""
        logger.info("Starting Identity Tracker")

        try:
            for message in self.consumer:
                logger.debug("Received message", topic=message.topic, partition=message.partition, offset=message.offset)
                self.process_sighting_event(message.value)
        except KeyboardInterrupt:
            logger.info("Shutting down Identity Tracker")
        except Exception as e:
            logger.error("Unexpected error", error=str(e))
        finally:
            self.consumer.close()
            self.producer.close()

# FastAPI app
app = FastAPI(title="Identity Tracker", version="1.0.0")

# Global tracker instance
tracker = IdentityTracker()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/persons/{person_id}", response_model=PersonData)
async def get_person(person_id: str):
    """Get tracking data for a specific person."""
    person_data = tracker.get_person_data(person_id)
    if not person_data:
        raise HTTPException(status_code=404, detail="Person not found")
    return person_data

@app.post("/track")
async def update_tracking(update: TrackingUpdate):
    """Manually update tracking data (for testing or external sources)."""
    try:
        for obj in update.objects:
            tracker.update_person_tracking(
                obj.person_id,
                obj.camera_id,
                obj.timestamp,
                obj.position,
                obj.customer_id
            )
        # Broadcast the update
        asyncio.create_task(tracker.broadcast_tracking_update(update))
        return {"status": "updated", "objects_count": len(update.objects)}
    except Exception as e:
        logger.error("Failed to update tracking", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.websocket("/ws/tracking")
async def websocket_tracking(websocket: WebSocket):
    """WebSocket endpoint for real-time tracking updates."""
    await websocket.accept()
    tracker.websocket_clients.append(websocket)
    logger.info("Tracking WebSocket client connected", client_count=len(tracker.websocket_clients))

    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for keep-alive
            await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
    except WebSocketDisconnect:
        tracker.websocket_clients.remove(websocket)
        logger.info("Tracking WebSocket client disconnected", client_count=len(tracker.websocket_clients))
    except Exception as e:
        logger.error("WebSocket error", error=str(e))
        if websocket in tracker.websocket_clients:
            tracker.websocket_clients.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    import threading

    # Start Kafka consumer in a separate thread
    def run_kafka_consumer():
        tracker.run()

    kafka_thread = threading.Thread(target=run_kafka_consumer, daemon=True)
    kafka_thread.start()

    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=config.service_port)