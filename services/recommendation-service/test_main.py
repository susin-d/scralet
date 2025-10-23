import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from config import config

# Mock the heavy imports to avoid connection issues
import sys
sys.modules['redis'] = MagicMock()
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.errors'] = MagicMock()

# Now import after mocking
from main import RecommendationService, ActionEvent

class TestActionEvent:
    def test_to_dict(self):
        event = ActionEvent("cust123", "zone1", ["prod1", "prod2"], "2023-01-01T00:00:00")
        expected = {
            'customer_id': 'cust123',
            'store_zone': 'zone1',
            'recommended_products': ['prod1', 'prod2'],
            'timestamp': '2023-01-01T00:00:00'
        }
        assert event.to_dict() == expected

class TestRecommendationService:
    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    def test_init(self, mock_producer, mock_consumer, mock_redis):
        service = RecommendationService()
        assert service.redis_client is not None
        assert service.consumer is not None
        assert service.producer is not None

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    def test_generate_recommendations(self, mock_producer, mock_consumer, mock_redis):
        mock_redis_instance = Mock()
        mock_redis_instance.get.return_value = '["prod1", "prod2"]'  # Mock customer history
        mock_redis.return_value = mock_redis_instance

        service = RecommendationService()
        recommendations = service.generate_recommendations("cust123", "zone1")
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    def test_publish_action_event(self, mock_producer, mock_consumer, mock_redis):
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='action-events', partition=0, offset=1)
        mock_producer_instance.send.return_value = mock_future
        mock_producer.return_value = mock_producer_instance

        service = RecommendationService()
        event = ActionEvent("cust123", "zone1", ["prod1", "prod2"], "2023-01-01T00:00:00")
        service.publish_action_event(event)

        mock_producer_instance.send.assert_called_once_with('action-events', event.to_dict())

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    def test_process_identified_event(self, mock_producer, mock_consumer, mock_redis):
        mock_redis_instance = Mock()
        mock_redis_instance.get.return_value = '["prod1", "prod2"]'
        mock_redis.return_value = mock_redis_instance

        service = RecommendationService()
        event_data = {
            'customer_id': 'cust123',
            'confidence': 98.5,
            'camera_id': 'cam1',
            'timestamp': '2023-01-01T00:00:00'
        }
        service.process_identified_event(event_data)

        # Verify that publish was called (assuming zone is extracted from camera_id)
        # This would need more mocking for full test

if __name__ == "__main__":
    pytest.main([__file__])