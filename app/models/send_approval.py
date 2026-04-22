import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class SendApproval(Base):
    __tablename__ = "send_approvals"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    token        = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    status       = Column(String, default="pending")  # pending | approved | cancelled
    queued_count = Column(Integer, default=0)
    subject_preview = Column(String, nullable=True)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    decided_at   = Column(DateTime(timezone=True), nullable=True)
