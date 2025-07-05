import re
from datetime import datetime, timedelta, timezone
from azure.storage.blob import BlobSasPermissions, generate_blob_sas
from azure.storage.blob.aio import BlobServiceClient
from core.config import settings


class AzureBlobStorageClient:
    """Client for uploading files and generating SAS URLs for Azure Blob Storage."""

    def __init__(self):
        self.account_name = None
        self.account_key = None

        # Parse connection string to get account name and key for SAS generation
        conn_parts = {
            part.split("=", 1)[0]: part.split("=", 1)[1]
            for part in settings.AZURE_STORAGE_CONNECTION_STRING.split(";")
        }
        self.account_name = conn_parts.get("AccountName")
        self.account_key = conn_parts.get("AccountKey")

        self.blob_service_client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.aclose()

    async def aclose(self):
        """Close the blob service client to prevent resource leaks."""
        try:
            await self.blob_service_client.close()
            print("Blob storage client resources closed.")
        except Exception as e:
            print(f"Error closing blob storage client resources: {e}")

    def sanitize_for_path(self, value: str) -> str:
        """Sanitizes a string to be safely used as a file/blob path component."""
        value = re.sub(r'[<>:"/\\|?*]', "_", value)
        value = re.sub(r"\s+", "_", value)
        return value.strip("_")

    async def upload_attachment(
        self, data: bytes, sender: str, internet_message_id: str, filename: str
    ) -> str:
        """Uploads attachment data to blob storage and returns the blob path."""
        sanitized_sender = self.sanitize_for_path(sender)
        sanitized_msg_id = self.sanitize_for_path(internet_message_id)
        sanitized_filename = self.sanitize_for_path(filename)

        blob_name = f"{sanitized_sender}/{sanitized_msg_id}/{sanitized_filename}"

        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_name
        )

        await blob_client.upload_blob(data, overwrite=True)
        print(f"Successfully uploaded '{filename}' to blob path: {blob_name}")
        return blob_name

    def get_blob_sas_url(self, blob_name: str) -> str:
        """Generates a SAS URL with read permissions valid for 1 hour."""
        if not self.account_name or not self.account_key:
            raise ValueError(
                "Account Name or Key not found in connection string. Cannot generate SAS token."
            )

        sas_token = generate_blob_sas(
            account_name=self.account_name,
            account_key=self.account_key,
            container_name=self.container_name,
            blob_name=blob_name,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        url = f"https://{self.account_name}.blob.core.windows.net/{self.container_name}/{blob_name}?{sas_token}"
        return url
