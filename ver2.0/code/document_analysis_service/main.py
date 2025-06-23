# document_analysis_service/main.py (Corrected Version)

from .service import DocumentAnalysisService

if __name__ == "__main__":
    try:
        # First, create an instance of the service.
        # If this fails (e.g., can't connect to RabbitMQ), the except block will catch it.
        analysis_service = DocumentAnalysisService()

        # If the instance is created successfully, then start waiting for messages.
        analysis_service.start_consuming()

    except KeyboardInterrupt:
        print("\nService stopped by user.")
    except Exception as e:
        # This will now catch any other errors, like connection failures.
        print(f"\n[ERROR] Could not start the Document Analysis Service.")
        print(f"      Reason: {e}")
        print(
            f"      Please check your RabbitMQ settings in the .env file (especially RABBITMQ_OUTPUT_QUEUE_NAME) and ensure RabbitMQ is running."
        )
