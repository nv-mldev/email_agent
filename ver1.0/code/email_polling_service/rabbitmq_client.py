import pika
import json
from core.config import settings


class RabbitMQClient:
    """
    A robust RabbitMQ client that uses a context manager (`with` statement)
    to ensure connections are handled correctly.
    """

    def __init__(self):
        """Initializes connection parameters."""
        self.connection_params = pika.ConnectionParameters(
            host=settings.RABBITMQ_HOST,
            port=settings.RABBITMQ_PORT,
            credentials=pika.PlainCredentials(
                settings.RABBITMQ_USER, settings.RABBITMQ_PASS
            ),
            heartbeat=600,  # Keep connection alive
            blocked_connection_timeout=300,
        )
        self.queue_name = settings.RABBITMQ_INPUT_QUEUE_NAME
        self._connection = None
        self._channel = None

    def __enter__(self):
        """Context manager entry point: establishes the connection."""
        try:
            print("[RMQ-CLIENT] Connecting to RabbitMQ server...")
            self._connection = pika.BlockingConnection(self.connection_params)
            self._channel = self._connection.channel()
            # Enable publisher confirms to guarantee message delivery
            self._channel.confirm_delivery()
            # Ensure the queue exists
            self._channel.queue_declare(queue=self.queue_name, durable=True)
            print(
                f"[RMQ-CLIENT] Connection successful. Ready to publish to '{self.queue_name}'."
            )
            return self
        except Exception as e:
            print(f"[RMQ-CLIENT-ERROR] Failed to connect to RabbitMQ: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit point: cleanly closes the connection."""
        if self._connection and self._connection.is_open:
            self._connection.close()
            print("[RMQ-CLIENT] RabbitMQ connection closed.")

    def publish_message(self, message_body: dict):
        """Publishes a message and waits for broker confirmation."""
        if not self._channel or self._channel.is_closed:
            raise ConnectionError(
                "RabbitMQ channel is not open. Call within a 'with' block."
            )

        message_str = json.dumps(message_body)

        try:
            # The mandatory=True flag will cause a message to be returned if it can't be routed.
            # The confirm_delivery() call ensures this is a blocking operation.
            self._channel.basic_publish(
                exchange="",
                routing_key=self.queue_name,
                body=message_str,
                properties=pika.BasicProperties(
                    delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                ),
                mandatory=True,
            )
            print(
                f"[RMQ-CLIENT] Successfully published AND CONFIRMED message for db_log_id: {message_body.get('db_log_id')}"
            )

        except pika.exceptions.UnroutableError:
            print(
                "[RMQ-CLIENT-ERROR] Message could not be delivered: The queue does not exist."
            )
            raise
        except Exception as e:
            print(f"[RM-CLIENT-ERROR] An unexpected error occurred during publish: {e}")
            raise
