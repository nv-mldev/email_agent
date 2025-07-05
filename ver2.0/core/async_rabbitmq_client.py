import json
import logging
from datetime import datetime, date
from typing import Dict, Any
import aio_pika
from .config import settings

logger = logging.getLogger(__name__)


def json_datetime_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError("Type %s not serializable" % type(obj))


class AsyncRabbitMQClient:
    """Async RabbitMQ client using aio_pika for non-blocking operations"""

    def __init__(self):
        self.rabbitmq_url = settings.RABBITMQ_URL
        self.connection = None
        self.channel = None

    async def connect(self):
        """Establish connection to RabbitMQ"""
        if not self.connection or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)

    async def close(self):
        """Close connection to RabbitMQ"""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("RabbitMQ connection closed.")
        except Exception as e:
            logger.error("Error closing RabbitMQ connection: %s", e)

    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def publish_job_to_queue(self, queue_name: str, message_body: Dict[str, Any]):
        """
        Publish a single job message to a specific queue.
        """
        try:
            if not self.channel:
                await self.connect()

            # Declare the queue to ensure it exists
            await self.channel.declare_queue(queue_name, durable=True)

            # Prepare the message
            message = aio_pika.Message(
                body=json.dumps(
                    message_body, default=json_datetime_serializer
                ).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )

            # Publish to queue
            await self.channel.default_exchange.publish(message, routing_key=queue_name)

            logger.info("Sent job to queue '%s'", queue_name)

        except Exception as e:
            logger.error("Failed to publish job to queue '%s': %s", queue_name, e)
            raise

    async def publish_event_to_fanout(
        self, exchange_name: str, event_body: Dict[str, Any]
    ):
        """
        Publish a single event to a fanout exchange.
        """
        try:
            if not self.channel:
                await self.connect()

            # Declare the fanout exchange
            exchange = await self.channel.declare_exchange(
                exchange_name, aio_pika.ExchangeType.FANOUT, durable=True
            )

            # Prepare the message
            message = aio_pika.Message(
                body=json.dumps(event_body, default=json_datetime_serializer).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                content_type="application/json",
            )

            # Publish to fanout exchange
            await exchange.publish(message, routing_key="")

            logger.info("Sent event to exchange '%s'", exchange_name)

        except Exception as e:
            logger.error(
                "Failed to publish event to exchange '%s': %s", exchange_name, e
            )
            raise

    async def consume_from_queue(self, queue_name: str, callback):
        """
        Start consuming messages from a queue with a callback function.
        """
        try:
            if not self.channel:
                await self.connect()

            # Declare the queue
            queue = await self.channel.declare_queue(queue_name, durable=True)

            # Start consuming
            await queue.consume(callback)
            logger.info("Started consuming from queue '%s'", queue_name)

        except Exception as e:
            logger.error("Failed to consume from queue '%s': %s", queue_name, e)
            raise


class AsyncRabbitMQPublisher:
    """
    Simplified async RabbitMQ publisher for one-off publishing operations.
    Automatically handles connection lifecycle.
    """

    @staticmethod
    async def publish_job(queue_name: str, message_body: Dict[str, Any]):
        """Publish a job message using automatic connection management"""
        async with AsyncRabbitMQClient() as client:
            await client.publish_job_to_queue(queue_name, message_body)

    @staticmethod
    async def publish_event(exchange_name: str, event_body: Dict[str, Any]):
        """Publish an event using automatic connection management"""
        async with AsyncRabbitMQClient() as client:
            await client.publish_event_to_fanout(exchange_name, event_body)
