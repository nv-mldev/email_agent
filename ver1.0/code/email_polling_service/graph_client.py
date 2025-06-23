# email_polling_service/graph_client.py

from core.config import settings
from azure.identity.aio import ClientSecretCredential
from msgraph.graph_service_client import GraphServiceClient
from msgraph.generated.users.item.messages.messages_request_builder import (
    MessagesRequestBuilder,
)
from msgraph.generated.models.message import Message
from kiota_abstractions.api_error import APIError


class GraphClient:
    """Client for interacting with the MS Graph API, as an async context manager."""

    def __init__(self):
        self.credential = ClientSecretCredential(
            tenant_id=settings.AZURE_TENANT_ID,
            client_id=settings.AZURE_CLIENT_ID,
            client_secret=settings.AZURE_CLIENT_SECRET,
        )
        self.client = None
        self.mailbox_address = settings.MAILBOX_ADDRESS

    async def __aenter__(self):
        scopes = ["https://graph.microsoft.com/.default"]
        self.client = GraphServiceClient(credentials=self.credential, scopes=scopes)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.credential:
            await self.credential.close()
        print("Polling Graph client resources closed.")

    async def fetch_unread_messages(self) -> list[Message]:
        print("Checking for unread messages...")
        try:
            query_params = (
                MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
                    select=[
                        "id",
                        "receivedDateTime",
                        "subject",
                        "from",
                        "isRead",
                        "hasAttachments",
                        "internetMessageId",
                        "sender",
                        "conversationId",
                        "toRecipients",
                        "ccRecipients",
                    ],
                    filter="isRead eq false",
                    top=50,
                )
            )
            request_config = (
                MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
                    query_parameters=query_params
                )
            )
            messages_page = await self.client.users.by_user_id(
                self.mailbox_address
            ).messages.get(request_configuration=request_config)
            return messages_page.value if messages_page and messages_page.value else []
        except APIError as e:
            print(f"Graph API Error fetching messages: {e.message}")
        return []

    async def mark_message_as_read(self, message_id: str):
        try:
            message_update = Message(is_read=True)
            await self.client.users.by_user_id(
                self.mailbox_address
            ).messages.by_message_id(message_id).patch(body=message_update)
            print(f"Successfully marked message {message_id} as read.")
        except APIError as e:
            print(f"Graph API Error marking message {message_id} as read: {e.message}")
