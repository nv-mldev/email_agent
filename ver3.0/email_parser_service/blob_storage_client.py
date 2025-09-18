import logging
import asyncio
from typing import Optional
from azure.storage.blob.aio import BlobServiceClient
from core.config import settings

logger = logging.getLogger(__name__)


class BlobStorageClient:
    """Async client for Azure Blob Storage operations."""

    def __init__(self):
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = settings.AZURE_STORAGE_CONTAINER_NAME
        self.blob_service_client = None

    async def __aenter__(self):
        """Async context manager entry."""
        if not self.connection_string:
            raise ValueError("Azure Storage connection string not configured")

        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.blob_service_client:
            await self.blob_service_client.close()

    async def upload_attachment(
        self, attachment_content: bytes, filename: str, email_id: str
    ) -> str:
        """
        Upload attachment to blob storage.

        Args:
            attachment_content: The file content as bytes
            filename: Original filename
            email_id: Email ID for organizing files

        Returns:
            Blob storage path/URL
        """
        try:
            # Create a unique blob name
            blob_name = f"emails/{email_id}/attachments/{filename}"

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_name
            )

            # Upload the file
            await blob_client.upload_blob(
                attachment_content,
                overwrite=True,
                metadata={"email_id": email_id, "original_filename": filename},
            )

            logger.info(
                "Uploaded attachment %s for email %s to blob storage",
                filename,
                email_id,
            )

            return blob_name

        except Exception as e:
            logger.error(
                "Failed to upload attachment %s for email %s: %s", filename, email_id, e
            )
            raise

    async def download_attachment(self, blob_name: str) -> Optional[bytes]:
        """
        Download attachment from blob storage.

        Args:
            blob_name: The blob storage path

        Returns:
            File content as bytes, or None if not found
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_name
            )

            download_stream = await blob_client.download_blob()
            content = await download_stream.readall()

            logger.info("Downloaded attachment from blob storage: %s", blob_name)
            return content

        except Exception as e:
            logger.error("Failed to download attachment %s: %s", blob_name, e)
            return None

    async def get_attachment_url(self, blob_name: str) -> Optional[str]:
        """
        Get a URL for accessing the attachment.

        Args:
            blob_name: The blob storage path

        Returns:
            Public URL or None if not found
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name, blob=blob_name
            )

            # For now, return the blob URL (you might want to generate SAS tokens)
            return blob_client.url

        except Exception as e:
            logger.error("Failed to get URL for attachment %s: %s", blob_name, e)
            return None

    async def list_email_attachments(self, email_id: str) -> list[dict]:
        """
        List all attachments for a specific email.

        Args:
            email_id: The email ID

        Returns:
            List of attachment info dictionaries
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )

            prefix = f"emails/{email_id}/attachments/"
            attachments = []

            async for blob in container_client.list_blobs(name_starts_with=prefix):
                attachments.append(
                    {
                        "blob_name": blob.name,
                        "filename": blob.name.split("/")[-1],
                        "size": blob.size,
                        "last_modified": blob.last_modified,
                        "metadata": blob.metadata,
                    }
                )

            return attachments

        except Exception as e:
            logger.error("Failed to list attachments for email %s: %s", email_id, e)
            return []
