# core/config.py

import os
import dotenv

# Load environment variables from the .env file in the project root
dotenv.load_dotenv()


class Settings:
    """Holds all application settings, loaded from environment variables."""

    def __init__(self):
        # Database
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")

        # MS Graph API
        self.AZURE_TENANT_ID: str = os.getenv("AZURE_TENANT_ID", "")
        self.AZURE_CLIENT_ID: str = os.getenv("AZURE_CLIENT_ID", "")
        self.AZURE_CLIENT_SECRET: str = os.getenv("AZURE_CLIENT_SECRET", "")

        # Azure Blob Storage
        self.AZURE_STORAGE_CONNECTION_STRING: str = os.getenv(
            "AZURE_STORAGE_CONNECTION_STRING", ""
        )
        self.AZURE_STORAGE_CONTAINER_NAME: str = os.getenv(
            "AZURE_STORAGE_CONTAINER_NAME", ""
        )

        # --- START: CORRECTED SECTION ---
        # Azure AI Document Intelligence (for document layout analysis)
        self.AZURE_DOCUMENTINTELLIGENCE_ENDPOINT: str = os.getenv(
            "AZURE_DOCUMENTINTELLIGENCE_ENDPOINT", ""
        )
        self.AZURE_DOCUMENTINTELLIGENCE_API_KEY: str = os.getenv(
            "AZURE_DOCUMENTINTELLIGENCE_API_KEY", ""
        )

        # Azure OpenAI Service (for email body summarization)
        self.AZURE_OPENAI_ENDPOINT: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        self.AZURE_OPENAI_API_KEY: str = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.AZURE_OPENAI_DEPLOYMENT_NAME: str = os.getenv(
            "AZURE_OPENAI_DEPLOYMENT_NAME", ""
        )
        # --- END: CORRECTED SECTION ---

        # RabbitMQ
        self.RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
        self.RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", 5672))
        self.RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
        self.RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASS", "guest")
        self.RABBITMQ_INPUT_QUEUE_NAME: str = os.getenv("RABBITMQ_INPUT_QUEUE_NAME", "")
        self.RABBITMQ_OUTPUT_QUEUE_NAME: str = os.getenv(
            "RABBITMQ_OUTPUT_QUEUE_NAME", ""
        )
        self.RABBITMQ_URL = (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@{self.RABBITMQ_HOST}/"
        )

        # Service Specific
        self.MAILBOX_ADDRESS: str = os.getenv("MAILBOX_ADDRESS", "")


# Create a single, global instance of the settings to be imported by other modules
settings = Settings()
