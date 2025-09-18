# core/models.py

import enum
from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from .database import Base


class ProcessingStatus(str, enum.Enum):
    RECEIVED = "RECEIVED"
    PARSING = "PARSING"
    PARSED = "PARSED"
    FAILED_PARSING = "FAILED_PARSING"
    ANALYZING = "ANALYZING"
    FAILED_ANALYSIS = "FAILED_ANALYSIS"
    COMPLETE = "COMPLETE"
    ARCHIVED_CC = "ARCHIVED_CC"


class RecipientRole(str, enum.Enum):
    TO = "TO"
    CC = "CC"
    UNKNOWN = "UNKNOWN"


class EmailProcessingLog(Base):
    __tablename__ = "email_processing_log"

    id = Column(Integer, primary_key=True)

    internet_message_id = Column(String(512), unique=True, nullable=False, index=True)
    conversation_id = Column(String(512), index=True)
    graph_message_id = Column(String(512), nullable=False)

    sender_address = Column(String(255))
    subject = Column(Text)
    body = Column(Text)
    email_summary = Column(Text)
    project_id = Column(String(100))  # Project ID field
    received_at = Column(DateTime(timezone=True), nullable=False)
    role_of_inbox = Column(Enum(RecipientRole), default=RecipientRole.UNKNOWN)

    status = Column(
        Enum(ProcessingStatus), nullable=False, default=ProcessingStatus.RECEIVED
    )
    status_updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )
    error_message = Column(Text)

    # Simplified - just store basic attachment info
    parsed_attachments_json = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
