import json
import time
from typing import List, Dict, Any
import structlog
import redis
import random
from kafka import KafkaConsumer, KafkaProducer
from kafka.errors import KafkaError

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

class ActionEvent:
    def __init__(self, customer_id: str, store_zone: str, recommended_products: List[str], timestamp: str):
        self.customer_id = customer_id
        self.store_zone = store_zone
        self.recommended_products = recommended_products
        self.timestamp = timestamp

    def to_dict(self):
        return {
            'customer_id': self.customer_id,
            'store_zone': self.store_zone,
            'recommended_products': self.recommended_products,
            'timestamp': self.timestamp
        }

class RecommendationService:
    def __init__(self):
        # Redis for customer history and zone-based recommendations
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            decode_responses=True
        )

        # Kafka consumer for customer-identified events
        self.consumer = KafkaConsumer(
            config.kafka_consumer_topic,
            bootstrap_servers=config.kafka_bootstrap_servers,
            group_id='recommendation-service-group',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )

        # Kafka producer for action-events
        self.producer = KafkaProducer(
            bootstrap_servers=config.kafka_bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            retries=5,
            acks='all'
        )

        logger.info("RecommendationService initialized")

    def get_customer_history(self, customer_id: str) -> List[str]:
        """Retrieve customer purchase history from Redis."""
        try:
            history_key = f"customer:{customer_id}:history"
            history = self.redis_client.get(history_key)
            if history:
                return json.loads(history)
            return []
        except Exception as e:
            logger.error("Failed to get customer history from Redis, using fallback", customer_id=customer_id, error=str(e))
            return []  # Fallback: empty history

    def get_zone_products(self, store_zone: str) -> List[str]:
        """Get products available in a specific store zone."""
        try:
            zone_key = f"zone:{store_zone}:products"
            products = self.redis_client.get(zone_key)
            if products:
                return json.loads(products)
            # Default products if zone not found
            return ["default_prod_1", "default_prod_2", "default_prod_3"]
        except Exception as e:
            logger.error("Failed to get zone products from Redis, using fallback", store_zone=store_zone, error=str(e))
            return ["default_prod_1", "default_prod_2", "default_prod_3"]  # Fallback: default products

    def generate_recommendations(self, customer_id: str, store_zone: str) -> List[str]:
        """Generate tailored product recommendations based on customer history and zone."""
        try:
            # Get customer purchase history
            history = self.get_customer_history(customer_id)

            # Get products available in the zone
            zone_products = self.get_zone_products(store_zone)

            # Simple recommendation logic: combine history-based and zone-based recommendations
            recommendations = []

            # Add products from history (if available in zone)
            for product in history:
                if product in zone_products and product not in recommendations:
                    recommendations.append(product)

            # Fill remaining slots with zone products
            remaining_slots = 5 - len(recommendations)
            available_products = [p for p in zone_products if p not in recommendations]
            recommendations.extend(random.sample(available_products, min(remaining_slots, len(available_products))))

            # Ensure we have at least some recommendations
            if not recommendations:
                recommendations = zone_products[:5]

            logger.info("Generated recommendations",
                       customer_id=customer_id,
                       store_zone=store_zone,
                       recommendations=recommendations)

            return recommendations

        except Exception as e:
            logger.error("Failed to generate recommendations",
                        customer_id=customer_id,
                        store_zone=store_zone,
                        error=str(e))
            return ["fallback_prod_1", "fallback_prod_2"]

    def extract_store_zone(self, camera_id: str) -> str:
        """Extract store zone from camera ID (simple logic: assume camera_id contains zone info)."""
        # Simple extraction: assume camera_id like "zone1_cam1" or just use camera_id as zone
        if '_' in camera_id:
            return camera_id.split('_')[0]
        return camera_id  # fallback

    def publish_action_event(self, event: ActionEvent):
        """Publish ActionEvent to Kafka."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                future = self.producer.send(config.kafka_producer_topic, event.to_dict())
                record_metadata = future.get(timeout=10)
                logger.info("Action event published",
                            topic=record_metadata.topic,
                            customer_id=event.customer_id,
                            store_zone=event.store_zone,
                            recommendations=event.recommended_products)
                return
            except Exception as e:
                logger.warning("Failed to publish action event to Kafka", attempt=attempt + 1, error=str(e))
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
        logger.error("Failed to publish action event to Kafka after all retries, event lost")

    def process_identified_event(self, event: Dict[str, Any]):
        """Process a single identified customer event."""
        try:
            customer_id = event['customer_id']
            camera_id = event['camera_id']
            timestamp = event['timestamp']

            # Extract store zone from camera_id
            store_zone = self.extract_store_zone(camera_id)

            # Generate recommendations
            recommendations = self.generate_recommendations(customer_id, store_zone)

            # Create and publish action event
            action_event = ActionEvent(
                customer_id=customer_id,
                store_zone=store_zone,
                recommended_products=recommendations,
                timestamp=timestamp
            )

            self.publish_action_event(action_event)

        except Exception as e:
            logger.error("Error processing identified event", error=str(e), event=event)

    def run(self):
        """Main loop to consume Kafka messages."""
        logger.info("Starting Recommendation Service")

        try:
            for message in self.consumer:
                logger.debug("Received message", topic=message.topic, partition=message.partition, offset=message.offset)
                self.process_identified_event(message.value)
        except KeyboardInterrupt:
            logger.info("Shutting down Recommendation Service")
        except Exception as e:
            logger.error("Unexpected error", error=str(e))
        finally:
            self.consumer.close()
            self.producer.close()

if __name__ == "__main__":
    service = RecommendationService()
    service.run()