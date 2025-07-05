import json
import asyncio
import logging
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import aio_pika

from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings
from api.schemas import EmailLogDetails
from .ai_clients import DocumentIntelligenceClientWrapper, OpenAIClientWrapper
from email_parser_service.blob_storage_client import AzureBlobStorageClient

logger = logging.getLogger(__name__)


class DocumentAnalysisServiceAsync:
    def __init__(self):
        self.doc_intel_client = DocumentIntelligenceClientWrapper()
        self.openai_client = OpenAIClientWrapper()
        self.blob_storage_client = AzureBlobStorageClient()

        # Thread pool for running sync Azure Document Intelligence calls
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

        self.rabbitmq_url = (
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
            f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/%2F"
        )
        self.input_queue = settings.RABBITMQ_OUTPUT_QUEUE_NAME
        self.connection = None
        self.channel = None
        self.shutdown_event = asyncio.Event()

    async def start(self):
        """Start the async document analysis service"""
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        input_queue = await self.channel.declare_queue(self.input_queue, durable=True)

        logger.info(
            "ASYNC DOCUMENT ANALYZER listening on queue: '%s'", self.input_queue
        )
        await input_queue.consume(self.callback)

        # Wait for shutdown signal
        await self.shutdown_event.wait()

    def shutdown(self):
        """Signal the service to shutdown gracefully"""
        self.shutdown_event.set()

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()

            # Shutdown thread pool
            self.thread_pool.shutdown(wait=True)

            # Close blob storage client
            await self.blob_storage_client.aclose()

            logger.info("Document analysis service resources cleaned up.")
        except Exception as e:
            logger.error("Error during cleanup: %s", e)

    async def callback(self, message: aio_pika.IncomingMessage):
        """Handle incoming messages from RabbitMQ"""
        async with message.process():
            try:
                message_data = json.loads(message.body.decode("utf-8"))
                await self.process_message_async(message_data)
            except Exception as e:
                logger.error("Error during message processing: %s", e)

    async def process_message_async(self, message_data: dict):
        """Process document analysis message asynchronously"""
        db_log_id = message_data.get("db_log_id")
        logger.info("Processing document analysis for DB Log ID: %s", db_log_id)

        try:
            with closing(next(get_db())) as db:
                log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                if not log_entry:
                    raise Exception(f"Log entry {db_log_id} not found.")

                log_entry.status = ProcessingStatus.ANALYZING
                db.commit()

                # Run email summarization in thread pool (OpenAI call)
                email_body_text = str(log_entry.body or "")
                summary = await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    self.openai_client.summarize_email_body,
                    email_body_text,
                )
                log_entry.email_summary = summary

                # Extract Purchase Order number from email body and subject
                email_content = (
                    f"Subject: {log_entry.subject or ''}\n\nBody: {email_body_text}"
                )
                po_number = await asyncio.get_event_loop().run_in_executor(
                    self.thread_pool,
                    self.openai_client.extract_purchase_order_number,
                    email_content,
                )
                log_entry.purchase_order_number = po_number if po_number else None

                attachments_data = log_entry.parsed_attachments_json or []
                updated_attachments_data = []

                for attachment in attachments_data:
                    updated_attachment = attachment.copy()
                    if "storage_path" in attachment:
                        # Get blob SAS URL
                        blob_url = self.blob_storage_client.get_blob_sas_url(
                            attachment["storage_path"]
                        )

                        # Run document analysis in thread pool
                        # (Azure Document Intelligence)
                        loop = asyncio.get_event_loop()
                        analysis_result = await loop.run_in_executor(
                            self.thread_pool,
                            self.doc_intel_client.split_and_identify_by_title,
                            blob_url,
                        )
                        updated_attachment["identified_documents"] = analysis_result

                    updated_attachments_data.append(updated_attachment)

                log_entry.parsed_attachments_json = updated_attachments_data
                log_entry.status = ProcessingStatus.PENDING_CONFIRMATION.value

                db.commit()
                db.refresh(log_entry)

                logger.info(
                    "Successfully analyzed and updated DB Log ID: %s", db_log_id
                )

                # Publish event notification
                await self._publish_analysis_complete_event(log_entry)

        except Exception as e:
            logger.error("FAILED document analysis for %s: %s", db_log_id, e)
            # Update status to failed
            try:
                with closing(next(get_db())) as db:
                    log_entry = (
                        db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                    )
                    if log_entry:
                        log_entry.status = ProcessingStatus.FAILED_ANALYSIS
                        log_entry.error_message = str(e)
                        db.commit()
            except Exception as db_error:
                logger.error("Failed to update error status: %s", db_error)
            raise

    async def _publish_analysis_complete_event(self, log_entry):
        """Publish analysis complete event to fanout exchange"""
        try:
            event_payload = {
                "type": "ANALYSIS_COMPLETE",
                "payload": EmailLogDetails.model_validate(log_entry).model_dump(
                    mode="json"
                ),
            }

            # Declare the fanout exchange
            exchange = await self.channel.declare_exchange(
                settings.RABBITMQ_UI_NOTIFY_EXCHANGE,
                aio_pika.ExchangeType.FANOUT,
                durable=True,
            )

            # Publish the event
            await exchange.publish(
                aio_pika.Message(
                    body=json.dumps(event_payload).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                ),
                routing_key="",  # Empty routing key for fanout exchange
            )

            logger.info(
                "Sent analysis complete event to exchange '%s'",
                settings.RABBITMQ_UI_NOTIFY_EXCHANGE,
            )

        except Exception as e:
            logger.error("Failed to publish analysis complete event: %s", e)
