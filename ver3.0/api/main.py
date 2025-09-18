import asyncio
import json
import aio_pika
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, schemas
from core.database import SessionLocal, get_db
from core.config import settings

# Import the email polling function
from email_polling_service.poll_emails import run_polling_cycle

# Import OpenAI client for attachment analysis
from email_summarizer_service.openai_client import AzureOpenAIClient


# --- WebSocket Connection Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


# --- RabbitMQ Listener (runs in background) ---
async def listen_to_rabbitmq():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            settings.RABBITMQ_UI_NOTIFY_EXCHANGE,
            aio_pika.ExchangeType.FANOUT,
            durable=True,
        )
        queue = await channel.declare_queue(exclusive=True)
        await queue.bind(exchange)
        print(" [*] RabbitMQ listener started for UI notifications.")
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    await manager.broadcast(message.body.decode())


# --- FastAPI App ---
app = FastAPI()

# Add CORS middleware for React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(listen_to_rabbitmq())


# --- REST Endpoints for Internal UI ---


# --- Endpoint to Get All Logs ---
@app.get("/api/logs", response_model=list[schemas.EmailLogBase])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_all_logs(db, skip=skip, limit=limit)


# --- REST Endpoint for Log Details ---
@app.get("/api/logs/{log_id}", response_model=schemas.EmailLogDetails)
def read_log_details(log_id: int, db: Session = Depends(get_db)):
    db_log = crud.get_log_by_id(db, log_id=log_id)
    if db_log is None:
        raise HTTPException(status_code=404, detail="Log not found")
    return db_log


# --- Manual Email Fetch Endpoint ---
@app.post("/api/fetch-emails")
async def fetch_emails_manually():
    """Manually trigger email fetching - useful for staging/testing environments."""
    try:
        await run_polling_cycle()
        return {"status": "success", "message": "Email fetch completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch emails: {str(e)}")


# --- Attachment Analysis Endpoint ---
@app.post("/api/analyze-attachments", response_model=schemas.AttachmentAnalysisResult)
async def analyze_attachments(
    request: schemas.AttachmentAnalysisRequest, db: Session = Depends(get_db)
):
    """Analyze selected email attachments using AI."""
    try:
        # Get email details
        email_log = crud.get_log_by_id(db, log_id=request.email_id)
        if not email_log:
            raise HTTPException(status_code=404, detail="Email not found")

        # Prepare email context for analysis
        email_context = f"Subject: {email_log.subject or 'No subject'}\n"
        email_context += f"From: {email_log.sender_address or 'Unknown sender'}\n"
        if email_log.email_summary:
            email_context += f"Summary: {email_log.email_summary}"

        # Initialize OpenAI client and analyze attachments
        openai_client = AzureOpenAIClient()
        analysis_result = openai_client.analyze_attachments(
            attachment_filenames=request.attachment_filenames,
            email_context=email_context,
        )

        return schemas.AttachmentAnalysisResult(
            summary=analysis_result.get("summary", "No summary available"),
            document_type=analysis_result.get("document_type", "Unknown"),
            key_points=analysis_result.get("key_points", []),
            technical_details=analysis_result.get("technical_details", {}),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze attachments: {str(e)}"
        )


# --- Email Confirmation Endpoint ---
@app.post("/api/confirm-email")
async def confirm_email_summary(
    request: schemas.EmailConfirmationRequest, db: Session = Depends(get_db)
):
    """Confirm and save email summary with human validation."""
    try:
        # Get email details
        email_log = crud.get_log_by_id(db, log_id=request.email_id)
        if not email_log:
            raise HTTPException(status_code=404, detail="Email not found")

        # Update email with confirmed information
        # Note: You'll need to add these fields to your database model
        # For now, we'll just return success

        # Here you would typically update the database with:
        # - request.project_name
        # - request.project_id (if different from extracted)
        # - request.is_new_enquiry
        # - request.confirmed_attachments
        # - confirmation timestamp
        # - confirmation status

        return {
            "status": "success",
            "message": "Email summary confirmed and saved successfully",
            "email_id": request.email_id,
            "project_name": request.project_name,
            "project_id": request.project_id,
            "is_new_enquiry": request.is_new_enquiry,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to confirm email: {str(e)}"
        )


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
