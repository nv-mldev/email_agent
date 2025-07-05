import asyncio
import json
import aio_pika
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from . import crud, schemas
from core.database import SessionLocal, get_db
from core.config import settings

# Import the email polling function
from email_polling_service.poll_emails import run_polling_cycle


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


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
