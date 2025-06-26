import pika
import json
import asyncio
from contextlib import closing
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings
from .graph_client import GraphClient
from .blob_storage_client import AzureBlobStorageClient

# A more robust check for supported attachments.
# We'll check the content type OR the file extension.
SUPPORTED_CONTENT_TYPES = ["application/pdf"]
SUPPORTED_FILE_EXTENSIONS = ".pdf"


def is_attachment_supported(attachment):
    """
    Checks if an attachment is supported by looking at its content type
    and its filename extension.
    """
    if attachment.content_type in SUPPORTED_CONTENT_TYPES:
        return True

    # Fallback check for mislabeled files like 'application/octet-stream'
    if attachment.name and attachment.name.lower().endswith(SUPPORTED_FILE_EXTENSIONS):
        print(
            f"  -> INFO: Processing file '{attachment.name}' based on its extension, despite content type being '{attachment.content_type}'."
        )
        return True

    return False


class EmailParserService:
    def __init__(self):
        self.rabbitmq_connection = pika.BlockingConnection(
            pika.URLParameters(
                f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/%2F"
            )
        )
        self.rabbitmq_channel = self.rabbitmq_connection.channel()
        self.rabbitmq_channel.confirm_delivery()
        self.rabbitmq_channel.queue_declare(
            queue=settings.RABBITMQ_INPUT_QUEUE_NAME, durable=True
        )
        self.rabbitmq_channel.queue_declare(
            queue=settings.RABBITMQ_OUTPUT_QUEUE_NAME, durable=True
        )

    async def process_message_async(self, message_body: dict):
        graph_message_id = message_body.get("graph_message_id")
        db_log_id = message_body.get("db_log_id")
        print(f"\n--- Processing message from queue. Graph ID: {graph_message_id} ---")

        graph_client = GraphClient()
        blob_client = AzureBlobStorageClient()

        with closing(next(get_db())) as db:
            log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
            if not log_entry:
                raise Exception(f"Failed to find log entry for DB ID {db_log_id}")

            try:
                log_entry.status = ProcessingStatus.PARSING
                db.commit()

                message = await graph_client.get_message_details(graph_message_id)
                if not message:
                    raise Exception(
                        f"Failed to fetch message details for {graph_message_id}"
                    )

                log_entry.body = message.body.content if message.body else ""

                uploaded_attachments = []
                if message.has_attachments:
                    attachments_meta = await graph_client.get_attachments_metadata(
                        graph_message_id
                    )
                    for att in attachments_meta:
                        # --- USE OUR NEW, SMARTER CHECK ---
                        if not is_attachment_supported(att):
                            print(
                                f"  -> Skipping unsupported attachment '{att.name}' of type '{att.content_type}'"
                            )
                            continue

                        if att.is_inline:
                            print(f"  -> Skipping inline attachment: {att.name}")
                            continue

                        content = await graph_client.get_attachment_content(
                            graph_message_id, att.id
                        )
                        if content:
                            blob_path = await blob_client.upload_attachment(
                                data=content,
                                sender=message.sender.email_address.address,
                                internet_message_id=message.internet_message_id,
                                filename=att.name,
                            )
                            uploaded_attachments.append(
                                {
                                    "original_filename": att.name,
                                    "storage_path": blob_path,
                                }
                            )

                log_entry.status = ProcessingStatus.PARSED
                log_entry.parsed_attachments_json = uploaded_attachments
                db.merge(log_entry)
                db.commit()
                print(f"Successfully parsed email. DB log ID: {db_log_id}")

                output_payload = {"db_log_id": db_log_id}  # Simplified payload

                print(
                    f"[PARSER-PRODUCER DEBUG] Publishing to queue: '{settings.RABBITMQ_OUTPUT_QUEUE_NAME}'"
                )
                self.rabbitmq_channel.basic_publish(
                    exchange="",
                    routing_key=settings.RABBITMQ_OUTPUT_QUEUE_NAME,
                    body=json.dumps(output_payload),
                    properties=pika.BasicProperties(
                        delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
                    ),
                )
                print(
                    f"Published AND CONFIRMED task for {db_log_id} to '{settings.RABBITMQ_OUTPUT_QUEUE_NAME}'"
                )

            except Exception as e:
                print(f"!! FAILED to process message for DB log {db_log_id}: {e}")
                db.rollback()
                log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                log_entry.status = ProcessingStatus.FAILED_PARSING
                log_entry.error_message = str(e)
                db.commit()
                raise
            finally:
                await graph_client.aclose()

    def callback(self, ch, method, properties, body):
        try:
            message_body = json.loads(body.decode("utf-8"))
            asyncio.run(self.process_message_async(message_body))
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error in callback, rejecting message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        self.rabbitmq_channel.basic_qos(prefetch_count=1)
        self.rabbitmq_channel.basic_consume(
            queue=settings.RABBITMQ_INPUT_QUEUE_NAME, on_message_callback=self.callback
        )
        print(
            f"[PARSER DEBUG] Listening on queue: '{settings.RABBITMQ_INPUT_QUEUE_NAME}'"
        )
        print(
            f"[*] Waiting for messages on '{settings.RABBITMQ_INPUT_QUEUE_NAME}'. To exit press CTRL+C"
        )
        self.rabbitmq_channel.start_consuming()
