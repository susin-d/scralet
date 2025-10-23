import json
import time
import requests
from typing import Dict, Any, List
import structlog
import httpx
from kafka import KafkaConsumer
from kafka.errors import KafkaError
from prometheus_client import start_http_server, Counter, Histogram, generate_latest
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import threading
import uvicorn

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

# Prometheus metrics
MESSAGES_PROCESSED = Counter('promotions_display_messages_processed_total', 'Total number of messages processed')
DISPLAY_COMMANDS_SENT = Counter('promotions_display_commands_sent_total', 'Total number of display commands sent')
PROCESSING_LATENCY = Histogram('promotions_display_processing_duration_seconds', 'Message processing duration in seconds')
REQUEST_COUNT = Counter('promotions_display_requests_total', 'Total number of requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('promotions_display_request_duration_seconds', 'Request duration in seconds', ['method', 'endpoint'])

class DisplayCommand:
    def __init__(self, screen_id: str, message: str, duration: int = 10):
        self.screen_id = screen_id
        self.message = message
        self.duration = duration

    def to_dict(self) -> Dict[str, Any]:
        return {
            'screen_id': self.screen_id,
            'message': self.message,
            'duration': self.duration
        }

class Promotion(BaseModel):
    title: str
    description: str
    discount: str
    validity: str
    target_loyalty_status: str = "all"  # "all", "gold", "silver", "bronze"

class PromotionResponse(BaseModel):
    id: str
    title: str
    description: str
    discount: str
    validity: str

class PromotionsDisplayService:
    def __init__(self):
        # Start Prometheus metrics server
        start_http_server(8000)
        self.consumer = KafkaConsumer(
            config.kafka_topic,
            bootstrap_servers=config.kafka_bootstrap_servers,
            auto_offset_reset='latest',
            enable_auto_commit=True,
            group_id='promotions-display-group',
            value_deserializer=lambda x: json.loads(x.decode('utf-8'))
        )
        self.promotions = []  # In-memory storage for promotions
        logger.info("PromotionsDisplayService initialized", store_zone=config.store_zone)

    def translate_recommendation_to_command(self, recommendation: Dict[str, Any]) -> DisplayCommand:
        """Translate recommendation into display command."""
        # Simple logic: based on user_id and product, create personalized offer
        user_id = recommendation.get('user_id', 'unknown')
        product = recommendation.get('product', 'general')
        screen_id = recommendation.get('screen_id', 'nearby_screen_1')  # Assume nearby screen

        message = f"Special offer for {user_id}: 20% off on {product}!"
        return DisplayCommand(screen_id, message, duration=15)

    def send_display_command(self, command: DisplayCommand):
        """Send command to signage API or simulate."""
        try:
            # Simulate sending to signage API
            logger.info("Sending display command", command=command.to_dict())
            # In real implementation, this would be:
            # response = requests.post(config.signage_api_url, json=command.to_dict())
            # response.raise_for_status()
            print(f"Display command sent: {command.to_dict()}")
            DISPLAY_COMMANDS_SENT.inc()
        except Exception as e:
            logger.error("Failed to send display command, command lost", error=str(e))

    def process_action_event(self, event: Dict[str, Any]):
        """Process incoming action event from Kafka."""
        with PROCESSING_LATENCY.time():
            logger.info("Processing action event", **event)
            # Assume event contains recommendation data
            command = self.translate_recommendation_to_command(event)
            self.send_display_command(command)
            MESSAGES_PROCESSED.inc()

    async def get_user_loyalty_status(self, user_id: str) -> str:
        """Fetch user loyalty status from user service."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{config.user_service_url}/customer/{user_id}")
                if response.status_code == 200:
                    user_data = response.json()
                    return user_data.get("loyalty_status", "bronze")
                else:
                    logger.warning("Failed to get user data", user_id=user_id, status=response.status_code)
                    return "bronze"
            except Exception as e:
                logger.error("Error calling user service", error=str(e))
                return "bronze"

    def run(self):
        """Main loop to consume Kafka messages."""
        logger.info("Starting Promotions Display Service")
        try:
            for message in self.consumer:
                self.process_action_event(message.value)
        except KeyboardInterrupt:
            logger.info("Service interrupted by user")
        except Exception as e:
            logger.error("Unexpected error", error=str(e))
        finally:
            self.consumer.close()
            logger.info("Service stopped")

# FastAPI app
app = FastAPI(title="Promotions Display Service", version="1.0.0")

service = PromotionsDisplayService()

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/metrics")
async def metrics():
    return generate_latest()

@app.post("/promotions", response_model=PromotionResponse)
async def create_promotion(promotion: Promotion):
    with REQUEST_LATENCY.labels(method='POST', endpoint='/promotions').time():
        try:
            logger.info("Creating new promotion", title=promotion.title)
            import uuid
            promo_id = str(uuid.uuid4())
            promo_dict = promotion.dict()
            promo_dict["id"] = promo_id
            service.promotions.append(promo_dict)

            REQUEST_COUNT.labels(method='POST', endpoint='/promotions', status='200').inc()
            logger.info("Promotion created successfully", id=promo_id)
            return PromotionResponse(**promo_dict)
        except Exception as e:
            REQUEST_COUNT.labels(method='POST', endpoint='/promotions', status='500').inc()
            logger.error("Error creating promotion", error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/promotions/{user_id}", response_model=List[PromotionResponse])
async def get_promotions(user_id: str):
    with REQUEST_LATENCY.labels(method='GET', endpoint='/promotions/{user_id}').time():
        try:
            logger.info("Retrieving promotions for user", user_id=user_id)
            loyalty_status = await service.get_user_loyalty_status(user_id)

            # Filter promotions based on loyalty status
            personalized_promotions = []
            for promo in service.promotions:
                target_status = promo.get("target_loyalty_status", "all")
                if target_status == "all" or target_status == loyalty_status:
                    personalized_promotions.append(PromotionResponse(**promo))

            REQUEST_COUNT.labels(method='GET', endpoint='/promotions/{user_id}', status='200').inc()
            logger.info("Promotions retrieved successfully", user_id=user_id, count=len(personalized_promotions))
            return personalized_promotions
        except Exception as e:
            REQUEST_COUNT.labels(method='GET', endpoint='/promotions/{user_id}', status='500').inc()
            logger.error("Error retrieving promotions", user_id=user_id, error=str(e))
            raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import threading

    # Start Kafka consumer in a separate thread
    def start_kafka_consumer():
        service.run()

    kafka_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    kafka_thread.start()

    # Start FastAPI server
    uvicorn.run(app, host="0.0.0.0", port=8002)