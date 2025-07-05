# This is the entry point for the long-running worker service
# It uses async_service.py for asynchronous email processing

import asyncio
import logging
import signal
import sys
from .async_service import EmailParserServiceAsync

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    service = EmailParserServiceAsync()

    # Set up signal handlers for graceful shutdown
    def signal_handler():
        logger.info("Received shutdown signal. Closing service...")
        service.shutdown()

    # Register signal handlers
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, signal_handler)
        loop.add_signal_handler(signal.SIGTERM, signal_handler)

    try:
        await service.start()
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
    except Exception as e:
        logger.error("A critical error occurred: %s", e)
    finally:
        await service.cleanup()


if __name__ == "__main__":
    try:
        logger.info("Starting Email Parser Service...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
    except Exception as e:
        logger.error("A critical error occurred: %s", e)
