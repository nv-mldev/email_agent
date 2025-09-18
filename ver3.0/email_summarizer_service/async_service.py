import json
import asyncio
import logging
from contextlib import closing
from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings
from core.async_rabbitmq_client import AsyncRabbitMQPublisher

from .openai_client import AzureOpenAIClient
import aio_pika

logger = logging.getLogger(__name__)


class EmailSummarizerServiceAsync:
    """Async service for generating email summaries using Azure OpenAI."""

    def __init__(self):
        self.rabbitmq_url = settings.RABBITMQ_URL
        self.input_queue = settings.RABBITMQ_OUTPUT_QUEUE_NAME
        self.ui_exchange = settings.RABBITMQ_UI_NOTIFY_EXCHANGE
        self.connection = None
        self.channel = None
        self.shutdown_event = asyncio.Event()
        self.openai_client = AzureOpenAIClient()

    async def start(self):
        """Start the summarizer service."""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        input_queue = await self.channel.declare_queue(self.input_queue, durable=True)

        logger.info("ASYNC SUMMARIZER listening on queue: '%s'", self.input_queue)
        await input_queue.consume(self.callback)

        # Wait for shutdown signal
        await self.shutdown_event.wait()

    def shutdown(self):
        """Signal the service to shutdown gracefully."""
        self.shutdown_event.set()

    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("Summarizer service resources cleaned up " "successfully.")
        except Exception as e:
            logger.error("Error during cleanup: %s", e)

    async def callback(self, message: aio_pika.IncomingMessage):
        """Process incoming messages from the parser service."""
        async with message.process():
            try:
                message_body = json.loads(message.body.decode("utf-8"))
                await self.process_message_async(message_body)
            except Exception as e:
                logger.error("Error during message processing: %s", e)

    async def process_message_async(self, message_body: dict):
        """Process a single email for summarization."""
        db_log_id = message_body.get("db_log_id")
        logger.info("Processing summarization for DB log ID: %s", db_log_id)

        with closing(next(get_db())) as db:
            log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
            if not log_entry:
                raise Exception(f"Failed to find log entry for DB ID {db_log_id}")

            try:
                log_entry.status = ProcessingStatus.ANALYZING
                db.commit()

                # Generate email summary
                if log_entry.body:
                    summary = self.openai_client.summarize_email(
                        email_body=log_entry.body,
                        subject=log_entry.subject or "",
                        sender=log_entry.sender_address or "",
                    )
                    log_entry.email_summary = summary

                    # Extract project ID
                    project_id = self.openai_client.extract_project_id(
                        email_body=log_entry.body, subject=log_entry.subject or ""
                    )
                    if project_id:
                        log_entry.project_id = project_id

                log_entry.status = ProcessingStatus.COMPLETE
                db.merge(log_entry)
                db.commit()

                logger.info("Successfully summarized email. DB log ID: %s", db_log_id)

                # Send UI notification
                await self.send_ui_notification(
                    {
                        "type": "EMAIL_SUMMARIZED",
                        "payload": {
                            "id": db_log_id,
                            "status": "COMPLETE",
                            "summary": log_entry.email_summary,
                            "project_id": log_entry.project_id,
                        },
                    }
                )

            except Exception as e:
                logger.error("FAILED summarization for %s: %s", db_log_id, e)
                db.rollback()
                log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                if log_entry:
                    log_entry.status = ProcessingStatus.FAILED_ANALYSIS
                    log_entry.error_message = str(e)
                    db.commit()
                raise

    async def send_ui_notification(self, payload: dict):
        """Send notification to UI via fanout exchange."""
        try:
            await AsyncRabbitMQPublisher.publish_event(
                exchange_name=self.ui_exchange, event_body=payload
            )
            logger.info("Sent UI notification: %s", payload["type"])
        except Exception as e:
            logger.error("Failed to send UI notification: %s", e)
