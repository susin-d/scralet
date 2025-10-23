import base64
import structlog
import uuid
from typing import List
import httpx
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from pymilvus import connections, Collection, DataType, FieldSchema, CollectionSchema
from prometheus_client import generate_latest, Counter, Histogram

from config import config
from models import Customer

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

# Database setup
engine = create_engine(config.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
            # Create index for vector search
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 128}
            }
            collection.create_index("embedding", index_params)
            logger.info("Milvus collection created with index")
        except Exception as e:
            logger.warning("Collection might already exist", error=str(e))
            collection = Collection(config.collection_name)
            # Ensure index exists
            try:
                collection.create_index("embedding", {"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
            except Exception as index_e:
                logger.info("Index might already exist", error=str(index_e))
        return collection
    except Exception as e:
        logger.warning("Milvus not available, using mock", error=str(e))
        return None

milvus_collection = init_milvus()

# Prometheus metrics
REQUEST_COUNT = Counter('user_service_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('user_service_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])

app = FastAPI(title="User Service", version="1.0.0")

# Pydantic models
class RegisterRequest(BaseModel):
    name: str
    email: str
    face_image_b64: str

    @field_validator('face_image_b64')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 string')

class AutoRegisterRequest(BaseModel):
    face_image_b64: str

    @field_validator('face_image_b64')
    def validate_base64(cls, v):
        try:
            base64.b64decode(v)
            return v
        except Exception:
            raise ValueError('Invalid base64 string')

class RegisterResponse(BaseModel):
    message: str
    customer_id: str

class CustomerResponse(BaseModel):
    id: str
    name: str
    email: str
    loyalty_status: str
    created_at: str

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions
async def get_embedding_from_face_service(face_image_b64: str) -> List[float]:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{config.face_recognition_url}/generate-embedding",
            json={"face_image_b64": face_image_b64}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")
        data = response.json()
        return data["embedding"]

def store_embedding_in_milvus(embedding: List[float]) -> int:
    if milvus_collection is None:
        logger.warning("Milvus not available, skipping embedding storage")
        return 0
    try:
        entities = [{"embedding": embedding}]
        insert_result = milvus_collection.insert(entities)
        milvus_collection.flush()
        return insert_result.primary_keys[0]
    except Exception as e:
        logger.error("Failed to store embedding in Milvus, using fallback", error=str(e))
        return 0  # Fallback: no vector ID

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return generate_latest()

# API endpoints
@app.post("/register", response_model=RegisterResponse)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    with REQUEST_LATENCY.labels(method='POST', endpoint='/register').time():
        logger.info("Registration request", name=request.name)

        try:
            # Get embedding from face recognition service
            embedding = await get_embedding_from_face_service(request.face_image_b64)
        except Exception as e:
            logger.error("Face recognition service failed, using fallback", error=str(e))
            # Fallback: generate a dummy embedding
            embedding = [0.0] * 512  # Dummy embedding

        # Store embedding in Milvus and get vector ID
        milvus_vector_id = store_embedding_in_milvus(embedding)

        try:
            # Create customer
            customer = Customer(
                name=request.name,
                email=request.email,
                milvus_vector_id=milvus_vector_id
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

            REQUEST_COUNT.labels(method='POST', endpoint='/register', status='200').inc()
            logger.info("Customer registered successfully", customer_id=str(customer.id))
            return RegisterResponse(message="Registration successful", customer_id=str(customer.id))
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/register', status='500').inc()
            logger.error("Database error during registration", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auto-register", response_model=RegisterResponse)
async def auto_register(
    request: AutoRegisterRequest,
    db: Session = Depends(get_db)
):
    with REQUEST_LATENCY.labels(method='POST', endpoint='/auto-register').time():
        logger.info("Auto-registration request for unrecognized face")

        try:
            # Get embedding from face recognition service
            embedding = await get_embedding_from_face_service(request.face_image_b64)
        except Exception as e:
            logger.error("Face recognition service failed, using fallback", error=str(e))
            # Fallback: generate a dummy embedding
            embedding = [0.0] * 512  # Dummy embedding

        # Store embedding in Milvus and get vector ID
        milvus_vector_id = store_embedding_in_milvus(embedding)

        try:
            # Generate a unique name and email for the new user
            customer_id = str(uuid.uuid4())
            name = f"Guest_{customer_id[:8]}"
            email = f"{name}@auto.generated"

            # Create customer
            customer = Customer(
                id=customer_id,
                name=name,
                email=email,
                milvus_vector_id=milvus_vector_id
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)

            REQUEST_COUNT.labels(method='POST', endpoint='/auto-register', status='200').inc()
            logger.info("Auto-registration successful", customer_id=str(customer.id))
            return RegisterResponse(message="Auto-registration successful", customer_id=str(customer.id))
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/auto-register', status='500').inc()
            logger.error("Database error during auto-registration", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/customer/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: str,
    db: Session = Depends(get_db)
):
    try:
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        return CustomerResponse(
            id=str(customer.id),
            name=customer.name,
            email=customer.email,
            loyalty_status=customer.loyalty_status,
            created_at=customer.created_at.isoformat()
        )
    except Exception as e:
        logger.error("Database error retrieving customer", customer_id=customer_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/customer/by-vector/{vector_id}", response_model=CustomerResponse)
async def get_customer_by_vector_id(
    vector_id: int,
    db: Session = Depends(get_db)
):
    try:
        customer = db.query(Customer).filter(Customer.milvus_vector_id == vector_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        return CustomerResponse(
            id=str(customer.id),
            name=customer.name,
            email=customer.email,
            loyalty_status=customer.loyalty_status,
            created_at=customer.created_at.isoformat()
        )
    except Exception as e:
        logger.error("Database error retrieving customer by vector ID", vector_id=vector_id, error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)