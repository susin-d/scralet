import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import base64
from io import BytesIO
from PIL import Image
from unittest.mock import patch, MagicMock

from main import app, get_db
from models import Base

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# Mock Milvus and other external dependencies
@pytest.fixture(autouse=True)
def mock_milvus():
    with patch('main.init_milvus') as mock_init:
        mock_collection = MagicMock()
        mock_init.return_value = mock_collection
        yield mock_collection

@pytest.fixture(autouse=True)
def mock_face_recognition():
    with patch('main.get_embedding_from_face_service') as mock_get:
        mock_get.return_value = [0.1] * 512  # Mock 512-dim embedding
        yield mock_get

@pytest.fixture(autouse=True)
def mock_email():
    with patch('main.send_verification_email', create=True) as mock_send:
        yield mock_send

# Helper function to create a dummy base64 image
def create_dummy_base64_image():
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='JPEG')
    img_str = base64.b64encode(buffer.getvalue()).decode()
    return img_str

@pytest.fixture
def dummy_image():
    return create_dummy_base64_image()

def test_register_customer(dummy_image, mock_milvus, mock_face_recognition, mock_email):
    response = client.post(
        "/register",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "face_image_b64": dummy_image
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "customer_id" in data
    assert data["message"] == "Registration successful"

def test_get_customer(mock_milvus, mock_face_recognition, mock_email):
    # First register a customer
    dummy_image = create_dummy_base64_image()
    register_response = client.post(
        "/register",
        json={
            "name": "Test User",
            "email": "test2@example.com",
            "face_image_b64": dummy_image
        }
    )
    customer_id = register_response.json()["customer_id"]

    # Try to get customer
    response = client.get(f"/customer/{customer_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test User"
    assert data["email"] == "test2@example.com"

    # Note: In a real test, you'd need to mock JWT tokens and other services
    # This is a basic structure for unit tests

def test_verify_email():
    # This would require mocking the email sending and database setup
    pass

def test_login():
    # This would require mocking the face recognition service and Milvus
    pass

def test_logout():
    # This would require JWT token setup
    pass

if __name__ == "__main__":
    pytest.main([__file__])