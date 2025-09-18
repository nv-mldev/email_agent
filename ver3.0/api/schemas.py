# api/schemas.py

from pydantic import BaseModel, ConfigDict
from datetime import datetime
from core.models import ProcessingStatus
from typing import List, Optional


class ParsedAttachment(BaseModel):
    """Simplified attachment info without document analysis."""

    original_filename: str
    storage_path: str | None = None


class AttachmentAnalysisRequest(BaseModel):
    """Request schema for attachment analysis."""

    email_id: int
    attachment_filenames: List[str]


class AttachmentAnalysisResult(BaseModel):
    """Result schema for attachment analysis."""

    summary: str
    document_type: str
    key_points: List[str]
    technical_details: Optional[dict] = None


class EmailConfirmationRequest(BaseModel):
    """Request schema for email confirmation."""

    email_id: int
    project_name: str
    project_id: str
    is_new_enquiry: bool
    confirmed_attachments: List[str] = []


class EmailLogBase(BaseModel):
    # This is the key change for Pydantic V2
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str | None
    sender_address: str | None
    status: ProcessingStatus
    received_at: datetime
    project_id: str | None = None


class EmailLogDetails(EmailLogBase):
    body: str | None
    email_summary: str | None
    parsed_attachments_json: list[ParsedAttachment] | None = []
    project_name: str | None = None
    is_new_enquiry: bool | None = None
