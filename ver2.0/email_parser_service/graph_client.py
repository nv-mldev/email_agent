import asyncio
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
import base64


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

    async def get_message_details(self, message_id: str) -> Message | None:
        """Fetches a single message with its body."""
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
            request_config = MessageItemRequestBuilder.MessageItemRequestBuilderGetRequestConfiguration(
                query_parameters=query_params
            )

            message = (
                await self.client.users.by_user_id(self.mailbox_address)
                .messages.by_message_id(message_id)
                .get(request_configuration=request_config)
            )
            return message
        except APIError as e:
            print(f"Graph API Error getting message for {message_id}: " f"{e.message}")
            return None

    async def get_attachments_metadata(self, message_id: str) -> list[Attachment]:
        """Fetches metadata for all attachments of a message."""
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
            print(
                f"Graph API Error getting attachments for {message_id}: " f"{e.message}"
            )
            return []

    async def get_attachment_content(
        self, message_id: str, attachment_id: str
    ) -> bytes | None:
        """Fetches the raw byte content of a specific attachment."""
        try:
            # Get the attachment metadata first
            attachment = (
                await self.client.users.by_user_id(self.mailbox_address)
                .messages.by_message_id(message_id)
                .attachments.by_attachment_id(attachment_id)
                .get()  # Use stream=True for large attachments
            )

            # Check if it's a FileAttachment and has content_bytes
            if isinstance(attachment, FileAttachment) and attachment.content_bytes:
                base64_encoded_content = attachment.content_bytes

                return base64.b64decode(base64_encoded_content)
            return None
        except APIError as e:
            print(
                f"Graph API Error getting attachment content for "
                f"{attachment_id}: {e.message}"
            )
            return None

    async def aclose(self):
        """Asynchronously closes the underlying HTTP client and credential."""
        try:
            # Close the Graph client's underlying HTTP session
            if hasattr(self.client, "request_adapter"):
                request_adapter = self.client.request_adapter

                # Try multiple ways to access and close the HTTP client
                http_client = None

                # Method 1: Try _http_client attribute
                if hasattr(request_adapter, "_http_client"):
                    http_client = getattr(request_adapter, "_http_client", None)

                # Method 2: Try http_client attribute (no underscore)
                elif hasattr(request_adapter, "http_client"):
                    http_client = getattr(request_adapter, "http_client", None)

                # Method 3: Try to get it through the adapter's session
                elif hasattr(request_adapter, "_client_session"):
                    http_client = getattr(request_adapter, "_client_session", None)

                # Method 4: Check for aiohttp session directly
                if http_client and hasattr(http_client, "close"):
                    print("Closing HTTP client session...")
                    await http_client.close()

                # Try to close the request adapter itself
                try:
                    if hasattr(request_adapter, "close"):
                        close_method = getattr(request_adapter, "close", None)
                        if close_method and callable(close_method):
                            if asyncio.iscoroutinefunction(close_method):
                                await close_method()
                            else:
                                close_method()
                except Exception as adapter_close_error:
                    print(
                        f"Warning: Could not close request adapter: "
                        f"{adapter_close_error}"
                    )

            # Close the credential
            if hasattr(self.credential, "close"):
                await self.credential.close()
            print("Parser Graph client resources closed.")
        except Exception as e:
            print(f"Error closing Parser Graph client resources: {e}")
