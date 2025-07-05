# email_polling_service/poll_emails.py

import asyncio
import json
import logging
from contextlib import closing
from datetime import datetime
from sqlalchemy.orm import Session
import aio_pika

from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus, RecipientRole
from core.config import settings
from .graph_client import GraphClient

logger = logging.getLogger(__name__)


def determine_role(message, mailbox_address: str) -> RecipientRole:
    """Determines if the mailbox was in the TO or CC field."""
    if any(
        rec.email_address.address.lower() == mailbox_address.lower()
        for rec in message.to_recipients
    ):
        return RecipientRole.TO
    if any(
        rec.email_address.address.lower() == mailbox_address.lower()
        for rec in message.cc_recipients
    ):
        return RecipientRole.CC
    return RecipientRole.UNKNOWN


async def run_polling_cycle():
    """Polls emails and publishes tasks using the async aio-pika library."""
    logger.info("Starting email polling cycle at %s", datetime.now().isoformat())

    connection = None
    # Use async with for GraphClient, and a try/finally for RabbitMQ connection
    async with GraphClient() as graph_client:
        try:
            # Connect to RabbitMQ asynchronously
            connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
            async with connection.channel() as channel:
                # Set QoS to ensure reliable publishing
                await channel.set_qos(prefetch_count=1)

                # Declare the queue to ensure it exists before publishing to it
                await channel.declare_queue(
                    settings.RABBITMQ_INPUT_QUEUE_NAME, durable=True
                )

                with closing(next(get_db())) as db:
                    unread_messages = await graph_client.fetch_unread_messages()
                    if not unread_messages:
                        logger.info("No new unread messages found.")
                        return

                    logger.info(
                        "Found %d unread email(s). Processing...", len(unread_messages)
                    )
                    for msg in unread_messages:
                        exists = (
                            db.query(EmailProcessingLog.id)
                            .filter_by(internet_message_id=msg.internet_message_id)
                            .first()
                        )
                        if exists:
                            logger.info(
                                "Duplicate email detected (ID: %s). Skipping.",
                                msg.internet_message_id,
                            )
                            # await graph_client.mark_message_as_read(msg.id)
                            continue

                        try:
                            role = determine_role(msg, settings.MAILBOX_ADDRESS)
                            sender_addr = (
                                msg.sender.email_address.address
                                if msg.sender and msg.sender.email_address
                                else "N/A"
                            )
                            new_log = EmailProcessingLog(
                                internet_message_id=msg.internet_message_id,
                                graph_message_id=msg.id,
                                conversation_id=msg.conversation_id,
                                sender_address=sender_addr,
                                subject=msg.subject,
                                received_at=msg.received_date_time,
                                role_of_inbox=role,
                                status=ProcessingStatus.RECEIVED,
                            )
                            db.add(new_log)
                            db.flush()

                            # Prepare and publish the message asynchronously
                            message_body = json.dumps(
                                {"db_log_id": new_log.id, "graph_message_id": msg.id}
                            ).encode()
                            message = aio_pika.Message(
                                body=message_body,
                                delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                            )

                            await channel.default_exchange.publish(
                                message, routing_key=settings.RABBITMQ_INPUT_QUEUE_NAME
                            )
                            logger.info(
                                "Successfully published message for db_log_id: %s",
                                new_log.id,
                            )

                            # await graph_client.mark_message_as_read(msg.id)

                            db.commit()
                            logger.info(
                                "Successfully processed and committed email. DB Log ID: %s",
                                new_log.id,
                            )

                        except Exception as e:
                            logger.error(
                                "Error during transaction for email %s: %s. Rolling back...",
                                msg.id,
                                e,
                            )
                            db.rollback()

        except Exception as e:
            logger.error("A critical error occurred during the polling cycle: %s", e)
        finally:
            # Ensure RabbitMQ connection is closed if it was opened
            if connection:
                await connection.close()
                logger.info("RabbitMQ connection closed.")

    logger.info("Email polling cycle finished at %s", datetime.now().isoformat())


if __name__ == "__main__":
    asyncio.run(run_polling_cycle())
