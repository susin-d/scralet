import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from config import config

# Mock the heavy imports to avoid tensorflow/numpy issues
import sys
from unittest.mock import MagicMock
sys.modules['mtcnn'] = MagicMock()
sys.modules['cv2'] = MagicMock()
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.errors'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['io'] = MagicMock()

# Now import after mocking
from main import EdgeProcessor, SightingEvent

class TestSightingEvent:
    def test_to_dict(self):
        event = SightingEvent("cam1", "2023-01-01T00:00:00", "base64data", (10, 20, 30, 40))
        expected = {
            'camera_id': 'cam1',
            'timestamp': '2023-01-01T00:00:00',
            'face_crop_b64': 'base64data',
            'person_bbox': (10, 20, 30, 40)
        }
        assert event.to_dict() == expected

class TestEdgeProcessor:
    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    def test_init(self, mock_kafka, mock_mtcnn, mock_hog):
        processor = EdgeProcessor()
        assert processor.hog is not None
        assert processor.mtcnn is not None
        assert processor.producer is not None

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    def test_detect_people(self, mock_kafka, mock_mtcnn, mock_hog):
        mock_hog_instance = Mock()
        mock_hog_instance.detectMultiScale.return_value = ([(10, 10, 50, 100)], [0.9])
        mock_hog.return_value = mock_hog_instance

        processor = EdgeProcessor()
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        boxes = processor.detect_people(frame)
        assert len(boxes) == 1
        assert boxes[0] == (10, 10, 60, 110)

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    def test_detect_people_error(self, mock_kafka, mock_mtcnn, mock_hog):
        mock_hog_instance = Mock()
        mock_hog_instance.detectMultiScale.side_effect = Exception("Test error")
        mock_hog.return_value = mock_hog_instance

        processor = EdgeProcessor()
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        boxes = processor.detect_people(frame)
        assert boxes == []

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    def test_detect_faces(self, mock_kafka, mock_mtcnn, mock_hog):
        mock_mtcnn_instance = Mock()
        mock_mtcnn_instance.detect_faces.return_value = [{'box': [10, 10, 50, 50]}]
        mock_mtcnn.return_value = mock_mtcnn_instance

        processor = EdgeProcessor()
        frame = np.zeros((200, 200, 3), dtype=np.uint8)
        faces = processor.detect_faces(frame)
        assert len(faces) == 1

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    def test_crop_face(self, mock_kafka, mock_mtcnn, mock_hog):
        processor = EdgeProcessor()
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
        face = {'box': [10, 10, 30, 30]}
        cropped = processor.crop_face(frame, face)
        assert cropped.shape == (30, 30, 3)

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    @patch('main.Image')
    @patch('main.io.BytesIO')
    def test_encode_image_to_base64(self, mock_bytesio, mock_image, mock_kafka, mock_mtcnn, mock_hog):
        # Mock PIL Image
        mock_pil_image = Mock()
        mock_image.fromarray.return_value = mock_pil_image

        # Mock BytesIO
        mock_buffer = Mock()
        mock_buffer.getvalue.return_value = b'fake_image_data'
        mock_bytesio.return_value = mock_buffer

        processor = EdgeProcessor()
        image = np.ones((10, 10, 3), dtype=np.uint8) * 255
        encoded = processor.encode_image_to_base64(image)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    @patch('main.time.sleep')
    def test_send_to_kafka_success(self, mock_sleep, mock_kafka, mock_mtcnn, mock_hog):
        mock_producer = Mock()
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='test', partition=0, offset=1)
        mock_producer.send.return_value = mock_future
        mock_kafka.return_value = mock_producer

        processor = EdgeProcessor()
        event = SightingEvent("cam1", "2023-01-01T00:00:00", "base64data", (10, 20, 30, 40))
        processor.send_to_kafka(event)
        mock_producer.send.assert_called_once()

    @patch('main.cv2.HOGDescriptor')
    @patch('main.MTCNN')
    @patch('main.KafkaProducer')
    @patch('main.time.sleep')
    @patch('main.KafkaError')
    def test_send_to_kafka_retry_success(self, mock_kafka_error, mock_sleep, mock_kafka, mock_mtcnn, mock_hog):
        # Create a custom exception class that inherits from Exception
        class MockKafkaError(Exception):
            pass

        mock_kafka_error.return_value = MockKafkaError

        mock_producer = Mock()
        mock_future = Mock()
        # First call raises MockKafkaError, second succeeds
        mock_future.get.side_effect = [MockKafkaError("Kafka error"), Mock(topic='test', partition=0, offset=1)]
        mock_producer.send.return_value = mock_future
        mock_kafka.return_value = mock_producer

        processor = EdgeProcessor()
        event = SightingEvent("cam1", "2023-01-01T00:00:00", "base64data", (10, 20, 30, 40))
        processor.send_to_kafka(event)
        assert mock_producer.send.call_count == 2

if __name__ == "__main__":
    pytest.main([__file__])