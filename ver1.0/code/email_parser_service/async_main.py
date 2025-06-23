import asyncio
from .async_service import EmailParserServiceAsync

if __name__ == "__main__":
    try:
        print("Starting Email Parser Service...")
        asyncio.run(EmailParserServiceAsync().start())
    except KeyboardInterrupt:
        print("Service stopped by user.")
    except Exception as e:
        print(f"A critical error occurred: {e}")
# This script is the entry point for the asynchronous email parser service.
# It initializes the EmailParserServiceAsync and starts it.
