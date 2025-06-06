import os
import dotenv


def load_environment():
    """Loads environment variables from a .env file."""
    dotenv.load_dotenv()


class Settings:
    """Class to hold all application settings."""

    def __init__(self):
        # MS Graph API - Required settings
        self.AZURE_TENANT_ID: str = self._get_required_env("AZURE_TENANT_ID")
        self.AZURE_CLIENT_ID: str = self._get_required_env("AZURE_CLIENT_ID")
        self.AZURE_CLIENT_SECRET: str = self._get_required_env("AZURE_CLIENT_SECRET")

        # RabbitMQ - Optional settings with defaults
        self.RABBITMQ_HOST: str = os.getenv("RABBITMQ_HOST", "localhost")
        self.RABBITMQ_PORT: int = int(os.getenv("RABBITMQ_PORT", "5672"))
        self.RABBITMQ_USER: str = os.getenv("RABBITMQ_USER", "guest")
        self.RABBITMQ_PASS: str = os.getenv("RABBITMQ_PASSWORD", "guest")
        self.RABBITMQ_QUEUE_NAME: str = os.getenv(
            "RABBITMQ_QUEUE_NAME", "email_parser_queue"
        )

        # Service Specific - Required settings
        self.MAILBOX_ADDRESS: str = self._get_required_env("MAILBOX_ADDRESS")
        self.POLLING_INTERVAL_SECONDS: int = int(os.getenv("POLLING_INTERVAL", "60"))

    def _get_required_env(self, env_var: str) -> str:
        """Get a required environment variable or raise an error."""
        value = os.getenv(env_var)
        if not value:
            raise ValueError(
                f"Required environment variable '{env_var}' is not set or empty"
            )
        return value


# Load environment at import time
load_environment()

# Create a single settings instance to be imported by other modules
settings = Settings()
