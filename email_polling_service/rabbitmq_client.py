import pika
import json
from .config import settings


class RabbitMQClient:
    """A client for interacting with RabbitMQ."""

    def __init__(self):
        """Initializes the RabbitMQ client with connection parameters from settings."""
        credentials = pika.PlainCredentials(
            settings.RABBITMQ_USER, settings.RABBITMQ_PASS
        )
        self.connection_params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=credentials,
        )
        self.queue_name = settings.RABBITMQ_QUEUE_NAME
        self._connection = None
        self._channel = None

    def _connect(self):
        """Establishes a connection and channel, declaring the queue."""
        if not self._connection or self._connection.is_closed:
            self._connection = pika.BlockingConnection(self.connection_params)
            self._channel = self._connection.channel()
            # Declare a durable queue to ensure messages are not lost if RabbitMQ restarts
            self._channel.queue_declare(queue=self.queue_name, durable=True)
            print(
                f"RabbitMQ connection established. Queue '{self.queue_name}' is ready."
            )

    def publish_message(self, message_body: dict):
        """
        Publishes a message to the configured queue.

        Args:
            message_body (dict): A dictionary representing the message to be published.
                                 It will be converted to a JSON string.
        """
        try:
            self._connect()
            if not self._channel:
                raise RuntimeError("RabbitMQ channel is not established.")
            message_str = json.dumps(message_body)
            self._channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=message_str,
                properties=pika.BasicProperties(
                    delivery_mode=2  # 2 means persistent delivery mode
                ),
            )
            print(
                f"Successfully published message for email_id: {message_body.get('id')}"
            )
        except Exception as e:
            print(f"Error publishing message to RabbitMQ: {e}")
            # In a real-world scenario, you might want to implement a retry mechanism here.

    def close(self):
        """Closes the RabbitMQ connection if it's open."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            print("RabbitMQ connection closed.")
