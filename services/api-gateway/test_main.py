import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import base64
from io import BytesIO
from PIL import Image

from main import app

client = TestClient(app)

# Mock httpx for external service calls
@pytest.fixture(autouse=True)
def mock_httpx():
    with patch('httpx.AsyncClient') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value.__aenter__.return_value = mock_instance
        mock_instance.post = MagicMock()
        mock_instance.post.return_value = MagicMock()
        mock_instance.post.return_value.status_code = 200
        mock_instance.post.return_value.json.return_value = {"message": "Registration successful", "customer_id": "123"}
        yield mock_instance

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

def test_register_success(dummy_image, mock_httpx):
    response = client.post(
        "/register",
        json={
            "name": "Test User",
            "face_image_b64": dummy_image
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "customer_id" in data
    assert data["message"] == "Registration successful"

def test_register_invalid_base64():
    response = client.post(
        "/register",
        json={
            "name": "Test User",
            "face_image_b64": "invalid_base64"
        }
    )
    assert response.status_code == 422  # Validation error

def test_register_user_service_failure(dummy_image, mock_httpx):
    mock_httpx.post.return_value.status_code = 500
    mock_httpx.post.return_value.text = "Internal Server Error"
    mock_httpx.post.return_value.json.side_effect = Exception("JSON decode error")

    response = client.post(
        "/register",
        json={
            "name": "Test User",
            "face_image_b64": dummy_image
        }
    )
    assert response.status_code == 500

if __name__ == "__main__":
    pytest.main([__file__])