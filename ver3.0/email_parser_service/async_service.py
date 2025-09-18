import json
import asyncio
import logging
import os
from contextlib import closing
from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings

from .graph_client import GraphClient
from .blob_storage_client import BlobStorageClient
import aio_pika

logger = logging.getLogger(__name__)


def is_allowed_attachment(
    filename: str | None, content_type: str | None = None
) -> bool:
    """
    Check if attachment should be processed based on file type.
    Only allow PDF, Excel, and DOCX files.
    """
    if not filename:
        return False

    # Get file extension
    file_ext = os.path.splitext(filename.lower())[1]

    # Allowed file extensions
    allowed_extensions = {
        ".pdf",
        ".xlsx",
        ".xls",
        ".xlsm",
        ".xlsb",  # Excel formats
        ".docx",
        ".doc",  # Word formats
    }

    # Check by file extension
    if file_ext in allowed_extensions:
        return True

    # Also check by content type if available
    if content_type:
        allowed_content_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
            "application/vnd.ms-excel",  # .xls
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
            "application/msword",  # .doc
        }

        if content_type.lower() in allowed_content_types:
            return True

    # Log filtered out files
    logger.info(
        f"Filtering out attachment: {filename} (ext: {file_ext}, type: {content_type})"
    )
    return False


class EmailParserServiceAsync:
    def __init__(self):
        self.rabbitmq_url = (
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
            f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/%2F"
        )
        self.input_queue = settings.RABBITMQ_INPUT_QUEUE_NAME
        self.output_queue = settings.RABBITMQ_OUTPUT_QUEUE_NAME
        self.connection = None
        self.channel = None
        self.shutdown_event = asyncio.Event()

    async def start(self):
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        await self.channel.set_qos(prefetch_count=1)

        self.output_channel = self.channel
        input_queue = await self.channel.declare_queue(self.input_queue, durable=True)

        logger.info("ASYNC PARSER listening on queue: '%s'", self.input_queue)
        await input_queue.consume(self.callback)

        # Wait for shutdown signal instead of running forever
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
            logger.info("Service resources cleaned up successfully.")
        except Exception as e:
            logger.error("Error during cleanup: %s", e)

    async def callback(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                message_body = json.loads(message.body.decode("utf-8"))
                await self.process_message_async(message_body)
            except Exception as e:
                logger.error("Error during message processing: %s", e)

    async def process_message_async(self, message_body: dict):
        graph_message_id = message_body.get("graph_message_id")
        db_log_id = message_body.get("db_log_id")
        logger.info("Processing Graph ID: %s", graph_message_id)

        async with GraphClient() as graph_client:
            with closing(next(get_db())) as db:
                log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                if not log_entry:
                    raise Exception(f"Failed to find log entry for DB ID {db_log_id}")

                try:
                    log_entry.status = ProcessingStatus.PARSING
                    db.commit()

                    message = await graph_client.get_message_details(graph_message_id)
                    if not message:
                        raise Exception(f"Message not found for {graph_message_id}")

                    log_entry.body = message.body.content if message.body else ""

                    # Process attachments if present
                    processed_attachments = []
                    if message.has_attachments:
                        logger.info("Processing attachments for email %s", db_log_id)
                        attachments = await graph_client.get_attachments_metadata(
                            graph_message_id
                        )

                        async with BlobStorageClient() as blob_client:
                            for attachment in attachments:
                                try:
                                    # Check if attachment is allowed (PDF, Excel, DOCX only)
                                    if not is_allowed_attachment(
                                        attachment.name,
                                        getattr(attachment, "content_type", None),
                                    ):
                                        logger.info(
                                            "Skipping filtered attachment: %s",
                                            attachment.name,
                                        )
                                        continue

                                    # Get attachment content
                                    content = await graph_client.get_attachment_content(
                                        graph_message_id, attachment.id
                                    )

                                    if content:
                                        # Upload to blob storage
                                        blob_path = await blob_client.upload_attachment(
                                            content,
                                            attachment.name
                                            or f"attachment_{attachment.id}",
                                            str(db_log_id),
                                        )

                                        processed_attachments.append(
                                            {
                                                "original_filename": attachment.name,
                                                "storage_path": blob_path,
                                                "size": len(content),
                                                "content_type": getattr(
                                                    attachment,
                                                    "content_type",
                                                    "unknown",
                                                ),
                                            }
                                        )

                                        logger.info(
                                            "Processed attachment %s for email %s",
                                            attachment.name,
                                            db_log_id,
                                        )

                                except Exception as e:
                                    logger.error(
                                        "Failed to process attachment %s for email %s: %s",
                                        attachment.name,
                                        db_log_id,
                                        e,
                                    )

                    # Update database with processed data
                    log_entry.status = ProcessingStatus.PARSED
                    log_entry.parsed_attachments_json = processed_attachments
                    db.merge(log_entry)
                    db.commit()

                    logger.info("Parsed email. DB log ID: %s", db_log_id)
                    await self.send_to_output_queue({"db_log_id": db_log_id})

                except Exception as e:
                    logger.error("FAILED parsing for %s: %s", db_log_id, e)
                    db.rollback()
                    log_entry = (
                        db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                    )
                    if log_entry:
                        log_entry.status = ProcessingStatus.FAILED_PARSING
                        log_entry.error_message = str(e)
                        db.commit()
                    raise

    async def send_to_output_queue(self, payload: dict):
        await self.output_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=self.output_queue,
        )
        logger.info("Published message to output queue: %s", payload)
