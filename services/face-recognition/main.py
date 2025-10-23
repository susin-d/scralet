import base64
import io
from typing import List
import structlog
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from deepface import DeepFace
import numpy as np
from PIL import Image
from prometheus_client import generate_latest, Counter, Histogram
from pymilvus import connections, Collection, DataType, FieldSchema, CollectionSchema

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

# Milvus setup
def init_milvus():
    try:
        connections.connect("default", host=config.milvus_host, port=config.milvus_port)
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=512)
        ]
        schema = CollectionSchema(fields, "Face embeddings collection")
        try:
            collection = Collection(config.collection_name, schema)
            logger.info("Milvus collection created or already exists")
        except Exception as e:
            logger.warning("Collection might already exist", error=str(e))
            collection = Collection(config.collection_name)
        return collection
    except Exception as e:
        logger.warning("Milvus not available, using mock", error=str(e))
        return None

milvus_collection = init_milvus()

# Prometheus metrics
REQUEST_COUNT = Counter('face_recognition_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('face_recognition_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])

app = FastAPI(title="Face Recognition Service", version="1.0.0")

class GenerateEmbeddingRequest(BaseModel):
    face_image_b64: str

    @field_validator('face_image_b64')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 string')

class GenerateEmbeddingResponse(BaseModel):
    embedding: List[float]

class RecognizeRequest(BaseModel):
    face_image_b64: str

    @field_validator('face_image_b64')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 string')

class TrackedObject(BaseModel):
    id: str
    name: str
    confidence: float
    loyalty_status: str

class RecognizeResponse(BaseModel):
    tracked_objects: List[TrackedObject]

def decode_base64_image(base64_string: str) -> Image.Image:
    try:
        image_data = base64.b64decode(base64_string)
        image = Image.open(io.BytesIO(image_data))
        return image
    except Exception as e:
        logger.error("Error decoding base64 image", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid image data")

def generate_embedding(image: Image.Image) -> List[float]:
    try:
        # Convert PIL to numpy array
        img_array = np.array(image)
        # Ensure RGB
        if len(img_array.shape) == 2:
            img_array = np.stack([img_array]*3, axis=-1)
        elif img_array.shape[2] == 4:
            img_array = img_array[:, :, :3]

        # Generate embedding using DeepFace with VGG-Face
        embedding = DeepFace.represent(img_array, model_name='VGG-Face', enforce_detection=False)
        return embedding[0]['embedding'] if isinstance(embedding, list) else embedding['embedding']
    except Exception as e:
        logger.error("Error generating embedding", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate embedding")

async def search_similar_faces(embedding: List[float], limit: int = 5) -> List[dict]:
    if milvus_collection is None:
        logger.warning("Milvus not available, returning empty results")
        return []

    try:
        milvus_collection.load()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = milvus_collection.search([embedding], "embedding", search_params, limit=limit)
        return [{"id": hit.id, "distance": hit.distance} for hit in results[0]]
    except Exception as e:
        logger.error("Failed to search Milvus", error=str(e))
        return []

async def get_user_data(user_id: str) -> dict:
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{config.user_service_url}/customer/{user_id}")
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("Failed to get user data", user_id=user_id, status=response.status_code)
                return None
        except Exception as e:
            logger.error("Error calling user service", error=str(e))
            return None

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return generate_latest()

@app.post("/generate-embedding", response_model=GenerateEmbeddingResponse)
async def generate_embedding_endpoint(request: GenerateEmbeddingRequest):
    with REQUEST_LATENCY.labels(method='POST', endpoint='/generate-embedding').time():
        try:
            logger.info("Received embedding generation request")

            # Decode image
            image = decode_base64_image(request.face_image_b64)

            # Generate embedding
            embedding = generate_embedding(image)

            REQUEST_COUNT.labels(method='POST', endpoint='/generate-embedding', status='200').inc()
            logger.info("Embedding generated successfully")
            return GenerateEmbeddingResponse(embedding=embedding)
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/generate-embedding', status='500').inc()
            logger.error("Unexpected error generating embedding", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/recognize", response_model=RecognizeResponse)
async def recognize_face(request: RecognizeRequest):
    with REQUEST_LATENCY.labels(method='POST', endpoint='/recognize').time():
        try:
            logger.info("Received face recognition request")

            # Decode image
            image = decode_base64_image(request.face_image_b64)

            # Generate embedding
            embedding = generate_embedding(image)

            # Search for similar faces in Milvus
            similar_faces = await search_similar_faces(embedding)

            tracked_objects = []
            for face in similar_faces:
                # Get user data from user service
                user_data = await get_user_data(str(face["id"]))
                if user_data:
                    confidence = max(0, 1 - face["distance"])  # Convert distance to confidence
                    tracked_obj = TrackedObject(
                        id=str(face["id"]),
                        name=user_data["name"],
                        confidence=confidence,
                        loyalty_status=user_data["loyalty_status"]
                    )
                    tracked_objects.append(tracked_obj)

            REQUEST_COUNT.labels(method='POST', endpoint='/recognize', status='200').inc()
            logger.info("Face recognition completed successfully")
            return RecognizeResponse(tracked_objects=tracked_objects)
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/recognize', status='500').inc()
            logger.error("Unexpected error during face recognition", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/users/{user_id}/face", response_model=TrackedObject)
async def get_user_face_data(user_id: str):
    try:
        logger.info("Received request for user face data", user_id=user_id)

        # Get user data from user service
        user_data = await get_user_data(user_id)
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        # For now, return with default confidence since we don't have the actual face data
        tracked_obj = TrackedObject(
            id=user_id,
            name=user_data["name"],
            confidence=1.0,  # Default confidence for known users
            loyalty_status=user_data["loyalty_status"]
        )

        REQUEST_COUNT.labels(method='GET', endpoint='/users/{user_id}/face', status='200').inc()
        logger.info("User face data retrieved successfully", user_id=user_id)
        return tracked_obj
    except HTTPException:
        raise
    except Exception as e:
        REQUEST_COUNT.labels(method='GET', endpoint='/users/{user_id}/face', status='500').inc()
        logger.error("Unexpected error retrieving user face data", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)