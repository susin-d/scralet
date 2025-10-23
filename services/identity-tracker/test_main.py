import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from config import config

# Mock the heavy imports to avoid connection issues
import sys
sys.modules['redis'] = MagicMock()
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.errors'] = MagicMock()
sys.modules['pymilvus'] = MagicMock()
sys.modules['pymilvus.connections'] = MagicMock()
sys.modules['pymilvus.Collection'] = MagicMock()
sys.modules['requests'] = MagicMock()
sys.modules['numpy'] = MagicMock()

# Now import after mocking
from main import IdentityTracker, IdentifiedCustomerEvent

class TestIdentifiedCustomerEvent:
    def test_to_dict(self):
        event = IdentifiedCustomerEvent("cust123", 98.5, "cam1", "2023-01-01T00:00:00")
        expected = {
            'customer_id': 'cust123',
            'confidence': 98.5,
            'camera_id': 'cam1',
            'timestamp': '2023-01-01T00:00:00'
        }
        assert event.to_dict() == expected

class TestIdentityTracker:
    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_init(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        tracker = IdentityTracker()
        assert tracker.redis_client is not None
        assert tracker.consumer is not None
        assert tracker.producer is not None
        assert tracker.collection is not None

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    @patch('main.requests.post')
    def test_get_face_embedding_success(self, mock_post, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_response = Mock()
        mock_response.json.return_value = {'embedding': [0.1, 0.2, 0.3]}
        mock_post.return_value = mock_response

        tracker = IdentityTracker()
        embedding = tracker.get_face_embedding("base64data")
        assert embedding == [0.1, 0.2, 0.3]

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    @patch('main.requests.post')
    def test_get_face_embedding_error(self, mock_post, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_post.side_effect = Exception("Request failed")

        tracker = IdentityTracker()
        # Should not raise exception, should return fallback embedding
        embedding = tracker.get_face_embedding("base64data")
        assert embedding == [0.0] * 512

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_search_similar_faces(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_collection_instance = Mock()
        mock_hit = Mock()
        mock_hit.entity.get.return_value = 'cust123'
        mock_hit.distance = 0.5
        mock_collection_instance.search.return_value = [[mock_hit]]
        mock_collection.return_value = mock_collection_instance

        tracker = IdentityTracker()
        results = tracker.search_similar_faces([0.1, 0.2, 0.3])
        assert len(results) == 1
        assert results[0]['customer_id'] == 'cust123'
        assert results[0]['distance'] == 0.5

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_update_session_confidence(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_redis_instance = Mock()
        mock_redis_instance.get.return_value = '80.0'
        mock_redis.return_value = mock_redis_instance

        tracker = IdentityTracker()
        tracker.update_session_confidence("session1", "cust123", 0.1)  # distance 0.1 -> confidence ~90

        # Verify set was called with higher confidence
        mock_redis_instance.set.assert_called()

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_check_identification_threshold_above(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_redis_instance = Mock()
        mock_redis_instance.keys.return_value = ['session:session1:cust123']
        mock_redis_instance.get.return_value = '98.0'
        mock_redis_instance.hgetall.return_value = {'camera_id': 'cam1', 'timestamp': '2023-01-01T00:00:00'}
        mock_redis.return_value = mock_redis_instance

        tracker = IdentityTracker()
        event = tracker.check_identification_threshold("session1")
        assert event is not None
        assert event.customer_id == 'cust123'
        assert event.confidence == 98.0

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_check_identification_threshold_below(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_redis_instance = Mock()
        mock_redis_instance.keys.return_value = ['session:session1:cust123']
        mock_redis_instance.get.return_value = '85.0'  # Below 95 threshold
        mock_redis.return_value = mock_redis_instance

        tracker = IdentityTracker()
        event = tracker.check_identification_threshold("session1")
        assert event is None

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_publish_identified_event(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_producer_instance = Mock()
        mock_future = Mock()
        mock_future.get.return_value = Mock(topic='customer-identified', partition=0, offset=1)
        mock_producer_instance.send.return_value = mock_future
        mock_producer.return_value = mock_producer_instance

        tracker = IdentityTracker()
        event = IdentifiedCustomerEvent("cust123", 98.5, "cam1", "2023-01-01T00:00:00")
        tracker.publish_identified_event(event)

        mock_producer_instance.send.assert_called_once_with('customer-identified', event.to_dict())

    @patch('main.redis.Redis')
    @patch('main.KafkaConsumer')
    @patch('main.KafkaProducer')
    @patch('main.connections')
    @patch('main.Collection')
    def test_delete_session(self, mock_collection, mock_connections, mock_producer, mock_consumer, mock_redis):
        mock_redis_instance = Mock()
        mock_redis_instance.keys.return_value = ['session:session1:cust123']
        mock_redis.return_value = mock_redis_instance

        tracker = IdentityTracker()
        tracker.delete_session("session1")

        mock_redis_instance.delete.assert_called()

if __name__ == "__main__":
    pytest.main([__file__])