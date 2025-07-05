from sqlalchemy.orm import Session
from core import models


def get_log_by_id(db: Session, log_id: int) -> models.EmailProcessingLog | None:
    return (
        db.query(models.EmailProcessingLog)
        .filter(models.EmailProcessingLog.id == log_id)
        .first()
    )


def get_all_logs(
    db: Session, skip: int = 0, limit: int = 100
) -> list[models.EmailProcessingLog]:
    return (
        db.query(models.EmailProcessingLog)
        .order_by(models.EmailProcessingLog.received_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
