# email_polling_service/poll_emails.py

import asyncio
import json
from contextlib import closing
from datetime import datetime
from sqlalchemy.orm import Session
import aio_pika

from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus, RecipientRole
from core.config import settings
from .graph_client import GraphClient


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
    print(f"--- Starting email polling cycle at {datetime.now().isoformat()} ---")

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
                        print("No new unread messages found.")
                        return

                    print(
                        f"Found {len(unread_messages)} unread email(s). Processing..."
                    )
                    for msg in unread_messages:
                        exists = (
                            db.query(EmailProcessingLog.id)
                            .filter_by(internet_message_id=msg.internet_message_id)
                            .first()
                        )
                        if exists:
                            print(
                                f"Duplicate email detected (ID: {msg.internet_message_id}). Skipping."
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
                            print(
                                f"[AIO-PIKA] Successfully published message for db_log_id: {new_log.id}"
                            )

                            # await graph_client.mark_message_as_read(msg.id)

                            db.commit()
                            print(
                                f"Successfully processed and committed email. DB Log ID: {new_log.id}"
                            )

                        except Exception as e:
                            print(
                                f"Error during transaction for email {msg.id}: {e}. Rolling back..."
                            )
                            db.rollback()

        except Exception as e:
            print(f"A critical error occurred during the polling cycle: {e}")
        finally:
            # Ensure RabbitMQ connection is closed if it was opened
            if connection:
                await connection.close()
                print("[AIO-PIKA] RabbitMQ connection closed.")

    print(f"--- Email polling cycle finished at {datetime.now().isoformat()} ---")


if __name__ == "__main__":
    asyncio.run(run_polling_cycle())
