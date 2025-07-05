import asyncio
import logging
from core.config import settings
from azure.identity.aio import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.models.message import Message
from msgraph.generated.models.attachment import Attachment
from msgraph.generated.models.file_attachment import FileAttachment
from msgraph.generated.users.item.messages.item.message_item_request_builder import (  # noqa: E501
    MessageItemRequestBuilder,
)
from kiota_abstractions.api_error import APIError
from kiota_abstractions.headers_collection import HeadersCollection  # <--- IMPORT THIS
import base64

logger = logging.getLogger(__name__)


class GraphClient:
    """Client for fetching full email details and attachments."""

    def __init__(self):
        scopes = ["https://graph.microsoft.com/.default"]
        self.credential = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET,
        )
        self.client = GraphServiceClient(credentials=self.credential, scopes=scopes)
        self.mailbox_address = settings.MAILBOX_ADDRESS

    async def __aenter__(self):
        """Async context manager entry"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - automatic cleanup"""
        await self.aclose()

    async def get_message_details(self, message_id: str) -> Message | None:
        """Fetches a single message with its body converted to plain text."""
        try:
            query_params = (
                MessageItemRequestBuilder.MessageItemRequestBuilderGetQueryParameters(
                    select=[
                        "id",
                        "subject",
                        "body",
                        "from",
                        "sender",
                        "hasAttachments",
                        "internetMessageId",
                        "receivedDateTime",
                    ]
                )
            )

            # --- MODIFIED LOGIC ---
            # Create a HeadersCollection object as expected by the SDK
            headers = HeadersCollection()
            headers.add("Prefer", 'outlook.body-content-type="text"')

            request_config = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
                query_parameters=query_params, headers=headers
            )
            # --- END OF MODIFIED LOGIC ---

            message = (
                await self.client.users.by_user_id(self.mailbox_address)
                .messages.by_message_id(message_id)
                .get(request_configuration=request_config)
            )
            return message
        except APIError as e:
            logger.error(
                "Graph API Error getting message for %s: %s", message_id, e.message
            )
            return None

    # ... (the rest of the file is unchanged) ...
    async def get_attachments_metadata(self, message_id: str) -> list[Attachment]:
        try:
            attachments_page = (
                await self.client.users.by_user_id(self.mailbox_address)
                .messages.by_message_id(message_id)
                .attachments.get()
            )
            return (
                attachments_page.value
                if attachments_page and attachments_page.value
                else []
            )
        except APIError as e:
            logger.error(
                "Graph API Error getting attachments for %s: %s", message_id, e.message
            )
            return []

    async def get_attachment_content(
        self, message_id: str, attachment_id: str
    ) -> bytes | None:
        try:
            attachment = (
                await self.client.users.by_user_id(self.mailbox_address)
                .messages.by_message_id(message_id)
                .attachments.by_attachment_id(attachment_id)
                .get()
            )
            if isinstance(attachment, FileAttachment) and attachment.content_bytes:
                base64_encoded_content = attachment.content_bytes
                return base64.b64decode(base64_encoded_content)
            return None
        except APIError as e:
            logger.error(
                "Graph API Error getting attachment content for %s: %s",
                attachment_id,
                e.message,
            )
            return None

    async def aclose(self):
        try:
            await self.credential.close()
            logger.info("Parser Graph client resources closed.")
        except Exception as e:
            logger.error("Error closing Parser Graph client resources: %s", e)
