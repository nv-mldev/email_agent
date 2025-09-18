import asyncio
import logging
from contextlib import closing
from datetime import datetime
import json

from core.database import get_db
from core.models import EmailProcessingLog, ProcessingStatus, RecipientRole
from core.config import settings
from core.async_rabbitmq_client import AsyncRabbitMQClient
from .graph_client import GraphClient
from api.schemas import EmailLogBase

logger = logging.getLogger(__name__)


def determine_role(message, mailbox_address: str) -> RecipientRole:
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
    logger.info("Starting email polling cycle at %s", datetime.now().isoformat())

    async with AsyncRabbitMQClient() as rabbitmq_client:
        async with GraphClient() as graph_client:
            with closing(next(get_db())) as db:
                unread_messages = await graph_client.fetch_unread_messages()
            if not unread_messages:
                logger.info("No new unread messages found.")
                return

            logger.info("Found %d unread email(s).", len(unread_messages))
            for msg in unread_messages:
                if (
                    db.query(EmailProcessingLog.id)
                    .filter_by(internet_message_id=msg.internet_message_id)
                    .first()
                ):
                    logger.info(
                        "Duplicate email (ID: %s). Marking as read and skipping.",
                        msg.internet_message_id,
                    )
                    await graph_client.mark_message_as_read(msg.id)
                    continue

                try:
                    new_log = EmailProcessingLog(
                        internet_message_id=msg.internet_message_id,
                        graph_message_id=msg.id,
                        subject=msg.subject,
                        sender_address=msg.sender.email_address.address,
                        received_at=msg.received_date_time,
                        role_of_inbox=determine_role(msg, settings.MAILBOX_ADDRESS),
                    )
                    db.add(new_log)
                    db.commit()
                    db.refresh(new_log)

                    # --- THIS IS THE CORRECTED PART ---
                    # The message body now matches what the parser service expects.
                    message_to_publish = {
                        "db_log_id": new_log.id,
                        "graph_message_id": new_log.graph_message_id,
                    }
                    await rabbitmq_client.publish_job_to_queue(
                        queue_name=settings.RABBITMQ_INPUT_QUEUE_NAME,
                        message_body=message_to_publish,
                    )
                    # --- END OF CORRECTION ---

                    event_payload = {
                        "type": "EMAIL_RECEIVED",
                        "payload": EmailLogBase.model_validate(new_log).model_dump(),
                    }
                    await rabbitmq_client.publish_event_to_fanout(
                        exchange_name=settings.RABBITMQ_UI_NOTIFY_EXCHANGE,
                        event_body=event_payload,
                    )

                    await graph_client.mark_message_as_read(msg.id)
                except Exception as e:
                    logger.error("Error processing email %s: %s", msg.id, e)
                    db.rollback()


if __name__ == "__main__":
    asyncio.run(run_polling_cycle())
