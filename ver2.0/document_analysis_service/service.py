import pika
import json
from contextlib import closing
from sqlalchemy.orm import Session
from azure.core.exceptions import HttpResponseError

from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus
from core.config import settings
from .ai_clients import DocumentIntelligenceClientWrapper, OpenAIClientWrapper
from email_parser_service.blob_storage_client import AzureBlobStorageClient


class DocumentAnalysisService:
    def __init__(self):
        self.rabbitmq_connection = pika.BlockingConnection(
            pika.URLParameters(
                f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/%2F"
            )
        )
        self.rabbitmq_channel = self.rabbitmq_connection.channel()
        self.rabbitmq_channel.queue_declare(
            queue=settings.RABBITMQ_OUTPUT_QUEUE_NAME, durable=True
        )

    def process_message(self, db_log_id: int):
        """Orchestrates the AI analysis for a given email log entry."""
        ai_doc_client = DocumentIntelligenceClientWrapper()
        ai_openai_client = OpenAIClientWrapper()
        blob_client = AzureBlobStorageClient()

        with closing(next(get_db())) as db:
            log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
            if not log_entry:
                raise Exception(f"Log entry with ID {db_log_id} not found.")

            try:
                log_entry.status = ProcessingStatus.ANALYZING
                db.commit()

                # Run analysis tasks sequentially. This is simpler and more robust.
                email_summary_result = ai_openai_client.summarize_email_body(
                    log_entry.body
                )

                attachments_data = log_entry.parsed_attachments_json or []
                for attachment in attachments_data:
                    blob_path = attachment.get("storage_path")
                    if blob_path:
                        try:
                            blob_url_with_sas = blob_client.get_blob_sas_url(blob_path)
                            analysis_result = ai_doc_client.split_and_identify_by_title(
                                blob_url_with_sas
                            )
                            attachment["identified_documents"] = analysis_result
                        except HttpResponseError as e:
                            if "InvalidContent" in e.message:
                                print(
                                    f"  -> WARNING: Attachment '{attachment['original_filename']}' is corrupted. Marking as failed."
                                )
                                attachment["identified_documents"] = [
                                    {
                                        "doc_type": "failed_analysis",
                                        "reason": "corrupted_or_unsupported",
                                    }
                                ]
                            else:
                                raise e

                # Consolidate all results
                log_entry.email_summary = email_summary_result
                log_entry.parsed_attachments_json = attachments_data
                log_entry.status = ProcessingStatus.PENDING_CONFIRMATION

                db.merge(log_entry)
                db.commit()
                print(f"Successfully analyzed and updated DB Log ID: {db_log_id}")

            except Exception as e:
                print(f"!! FAILED analysis for DB log {db_log_id}: {e}")
                db.rollback()
                log_entry = db.query(EmailProcessingLog).filter_by(id=db_log_id).first()
                log_entry.status = ProcessingStatus.FAILED_ANALYSIS
                log_entry.error_message = str(e)
                db.commit()
                raise

    def callback(self, ch, method, properties, body):
        """Synchronous callback that processes one message at a time."""
        message_body = json.loads(body.decode("utf-8"))
        db_log_id = message_body.get("db_log_id")
        print(
            f"\n[ANALYZER] Received message for DB Log ID: {db_log_id}. Starting processing..."
        )
        try:
            # Directly call the synchronous processing function. No asyncio needed.
            self.process_message(db_log_id)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(
                f"[ANALYZER] Successfully processed and acknowledged message for DB Log ID: {db_log_id}"
            )
        except Exception as e:
            print(
                f"\n[ANALYZER-ERROR] A critical error occurred while processing message for DB Log ID: {db_log_id}."
            )
            print(f"      Reason: {e}")
            print(f"      The message will be rejected and not requeued.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start_consuming(self):
        self.rabbitmq_channel.basic_qos(prefetch_count=1)
        self.rabbitmq_channel.basic_consume(
            queue=settings.RABBITMQ_OUTPUT_QUEUE_NAME, on_message_callback=self.callback
        )
        print(
            f"[ANALYZER-CONSUMER DEBUG] Listening on queue: '{settings.RABBITMQ_OUTPUT_QUEUE_NAME}'"
        )
        print(
            f"[*] Waiting for analysis tasks on '{settings.RABBITMQ_OUTPUT_QUEUE_NAME}'. To exit press CTRL+C"
        )
        self.rabbitmq_channel.start_consuming()
