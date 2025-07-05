# api/schemas.py

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from core.models import ProcessingStatus, RecipientRole


class IdentifiedDocument(BaseModel):
    doc_type: str
    confidence: float
    start_page: int
    end_page: int
    reason: str | None = None


class ParsedAttachment(BaseModel):
    original_filename: str
    storage_path: str
    identified_documents: list[IdentifiedDocument] = []


class EmailLogBase(BaseModel):
    # This is the key change for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str | None
    sender_address: str | None
    status: ProcessingStatus
    received_at: datetime
    purchase_order_number: str | None = None


class EmailLogDetails(EmailLogBase):
    body: str | None
    email_summary: str | None
    parsed_attachments_json: list[ParsedAttachment] | None = []
