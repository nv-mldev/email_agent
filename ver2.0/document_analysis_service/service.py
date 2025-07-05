import json
import logging
from contextlib import closing
import pika

from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings
from core.rabbitmq_client import RabbitMQClient
from api.schemas import EmailLogDetails
from .ai_clients import DocumentIntelligenceClientWrapper, OpenAIClientWrapper
from email_parser_service.blob_storage_client import AzureBlobStorageClient

logger = logging.getLogger(__name__)


class DocumentAnalysisService:
    def __init__(self):
        self.doc_intel_client = DocumentIntelligenceClientWrapper()
        self.openai_client = OpenAIClientWrapper()
        self.blob_storage_client = AzureBlobStorageClient()

        self.rabbitmq_client = RabbitMQClient()
        self.input_queue = settings.RABBITMQ_OUTPUT_QUEUE_NAME

    def start_consuming(self):
        connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=self.input_queue, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=self.input_queue, on_message_callback=self.on_message
        )
        logger.info(
            "Waiting for analysis tasks on '%s'. To exit press CTRL+C", self.input_queue
        )
        channel.start_consuming()

    def on_message(self, channel, method, properties, body):
        message_data = json.loads(body)
        db_log_id = message_data.get("db_log_id")

        logger.info(
            "Received message for DB Log ID: %s. Starting processing...", db_log_id
        )
        try:
            self.process_message(db_log_id)
            channel.basic_ack(delivery_tag=method.delivery_tag)
            logger.info(
                "Successfully processed and acknowledged message for DB Log ID: %s",
                db_log_id,
            )
        except Exception as e:
            logger.error(
                "A critical error occurred while processing message for DB Log ID: %s.",
                db_log_id,
            )
            logger.error("Reason: %s", e)
            logger.info("The message will be rejected and not requeued.")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def process_message(self, db_log_id: int):
        with closing(next(get_db())) as db:
            log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
            if not log_entry:
                raise Exception(f"Log entry {db_log_id} not found.")

            log_entry.status = ProcessingStatus.ANALYZING
            db.commit()

            summary = self.openai_client.summarize_email_body(log_entry.body or "")
            log_entry.email_summary = summary

            # Extract PO number from email subject and body
            email_content = (
                f"Subject: {log_entry.subject or ''}\n\n"
                f"Body: {log_entry.body or ''}"
            )
            po_number = self.openai_client.extract_purchase_order_number(email_content)
            log_entry.purchase_order_number = po_number

            attachments_data = log_entry.parsed_attachments_json or []
            updated_attachments_data = []

            # Process attachments if they exist
            for attachment in attachments_data:
                updated_attachment = attachment.copy()
                if "storage_path" in attachment:

                    # --- THIS IS THE CORRECTED LINE ---
                    # Changed get_blob_url_with_sas -> get_blob_sas_url
                    blob_url = self.blob_storage_client.get_blob_sas_url(
                        attachment["storage_path"]
                    )
                    # --- END OF CORRECTION ---

                    analysis_result = self.doc_intel_client.split_and_identify_by_title(
                        blob_url
                    )
                    updated_attachment["identified_documents"] = analysis_result

                updated_attachments_data.append(updated_attachment)

            log_entry.parsed_attachments_json = updated_attachments_data

            # Always move to PENDING_CONFIRMATION, whether attachments exist
            log_entry.status = ProcessingStatus.PENDING_CONFIRMATION

            db.commit()
            db.refresh(log_entry)
            logger.info("Successfully analyzed and updated DB Log ID: %s", db_log_id)

            event_payload = {
                "type": "ANALYSIS_COMPLETE",
                "payload": EmailLogDetails.model_validate(log_entry).model_dump(
                    mode="json"
                ),
            }
            self.rabbitmq_client.publish_event_to_fanout(
                settings.RABBITMQ_UI_NOTIFY_EXCHANGE, event_payload
            )
            logger.info(
                "Sent event to exchange '%s'", settings.RABBITMQ_UI_NOTIFY_EXCHANGE
            )
