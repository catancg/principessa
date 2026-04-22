import uuid
from sqlalchemy import Column, DateTime, Integer, Text, func
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class EmailVariant(Base):
    __tablename__ = "email_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generation_id = Column(UUID(as_uuid=True), nullable=False)
    campaign_type = Column(Text, nullable=False, default="weekly_promo")
    variant_index = Column(Integer, nullable=False)  # 1 or 2

    # pending_approval | approved | rejected | sent
    status = Column(Text, nullable=False, default="pending_approval")

    # ── inbox fields ──────────────────────────────────────────────────────────
    subject_line = Column(Text, nullable=False)
    preview_text = Column(Text)

    # ── template gaps filled by the AI ───────────────────────────────────────
    headline = Column(Text, nullable=False)           # hero headline
    highlight_phrase = Column(Text, nullable=False)   # yellow-highlighted phrase
    body_intro = Column(Text, nullable=False)         # sentence after the highlight

    block_1_emoji = Column(Text, nullable=False)
    block_1_title = Column(Text, nullable=False)
    block_1_text = Column(Text, nullable=False)

    block_2_emoji = Column(Text, nullable=False)
    block_2_title = Column(Text, nullable=False)
    block_2_text = Column(Text, nullable=False)

    closing_message = Column(Text, nullable=False)

    # ── metadata ─────────────────────────────────────────────────────────────
    ai_prompt = Column(Text)
    approval_token = Column(UUID(as_uuid=True), nullable=False, unique=True, default=uuid.uuid4)
    reviewer_notes = Column(Text)
    approved_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
