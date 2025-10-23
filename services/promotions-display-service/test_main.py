import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from config import config

# Mock the heavy imports to avoid issues
import sys
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.errors'] = MagicMock()
sys.modules['requests'] = MagicMock()

# Now import after mocking
from main import PromotionsDisplayService, DisplayCommand

class TestDisplayCommand:
    def test_to_dict(self):
        command = DisplayCommand("screen1", "Hello World", 10)
        expected = {
            'screen_id': 'screen1',
            'message': 'Hello World',
            'duration': 10
        }
        assert command.to_dict() == expected

class TestPromotionsDisplayService:
    @patch('main.KafkaConsumer')
    def test_init(self, mock_consumer):
        service = PromotionsDisplayService()
        assert service.consumer is not None

    @patch('main.KafkaConsumer')
    def test_translate_recommendation_to_command(self, mock_consumer):
        service = PromotionsDisplayService()
        recommendation = {
            'user_id': 'user123',
            'product': 'coffee',
            'screen_id': 'screen_nearby'
        }
        command = service.translate_recommendation_to_command(recommendation)
        assert command.screen_id == 'screen_nearby'
        assert 'user123' in command.message
        assert 'coffee' in command.message

    @patch('main.KafkaConsumer')
    @patch('builtins.print')
    def test_send_display_command(self, mock_print, mock_consumer):
        service = PromotionsDisplayService()
        command = DisplayCommand("screen1", "Test message")
        service.send_display_command(command)
        mock_print.assert_called_once()

    @patch('main.KafkaConsumer')
    def test_process_action_event(self, mock_consumer):
        service = PromotionsDisplayService()
        event = {
            'user_id': 'user456',
            'product': 'tea'
        }
        with patch.object(service, 'translate_recommendation_to_command') as mock_translate, \
             patch.object(service, 'send_display_command') as mock_send:
            mock_translate.return_value = DisplayCommand("screen1", "Test")
            service.process_action_event(event)
            mock_translate.assert_called_once_with(event)
            mock_send.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__])