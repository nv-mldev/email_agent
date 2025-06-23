import json
import asyncio
from contextlib import closing
from sqlalchemy.orm import Session
from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings

from .graph_client import GraphClient
from .blob_storage_client import AzureBlobStorageClient
import aio_pika

SUPPORTED_CONTENT_TYPES = ["application/pdf"]
SUPPORTED_FILE_EXTENSIONS = ".pdf"


def is_attachment_supported(attachment):
    if attachment.content_type in SUPPORTED_CONTENT_TYPES:
        return True
    if attachment.name and attachment.name.lower().endswith(SUPPORTED_FILE_EXTENSIONS):
        print(
            f"  -> INFO: Processing file '{attachment.name}' based on extension fallback."
        )
        return True
    return False


class EmailParserServiceAsync:
    def __init__(self):
        self.rabbitmq_url = (
            f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
            f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/%2F"
        )
        self.input_queue = settings.RABBITMQ_INPUT_QUEUE_NAME
        self.output_queue = settings.RABBITMQ_OUTPUT_QUEUE_NAME

    async def start(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)

        self.output_channel = channel
        input_queue = await channel.declare_queue(self.input_queue, durable=True)

        print(f"[ASYNC PARSER] Listening on queue: '{self.input_queue}'")
        await input_queue.consume(self.callback)

        await asyncio.Future()  # Run forever

    async def callback(self, message: aio_pika.IncomingMessage):
        async with message.process():
            try:
                message_body = json.loads(message.body.decode("utf-8"))
                await self.process_message_async(message_body)
            except Exception as e:
                print(f"Error during message processing: {e}")

    async def process_message_async(self, message_body: dict):
        graph_message_id = message_body.get("graph_message_id")
        db_log_id = message_body.get("db_log_id")
        print(f"\n--- Processing Graph ID: {graph_message_id} ---")

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
                    raise Exception(f"Message not found for {graph_message_id}")

                log_entry.body = message.body.content if message.body else ""

                uploaded_attachments = []
                if message.has_attachments:
                    attachments_meta = await graph_client.get_attachments_metadata(
                        graph_message_id
                    )
                    for att in attachments_meta:
                        if not is_attachment_supported(att) or att.is_inline:
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

                print(f"Parsed email. DB log ID: {db_log_id}")
                await self.send_to_output_queue({"db_log_id": db_log_id})

            except Exception as e:
                print(f"!! FAILED parsing for {db_log_id}: {e}")
                db.rollback()
                log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                log_entry.status = ProcessingStatus.FAILED_PARSING
                log_entry.error_message = str(e)
                db.commit()
                raise
            finally:
                await graph_client.aclose()

    async def send_to_output_queue(self, payload: dict):
        await self.output_channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            ),
            routing_key=self.output_queue,
        )
        print(f"✅ Published message to output queue: {payload}")
