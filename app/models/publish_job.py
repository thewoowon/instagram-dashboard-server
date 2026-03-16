from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class PublishJob(Base):
    __tablename__ = "publish_jobs"

    post_draft_id = Column(UUID(as_uuid=True), ForeignKey("post_drafts.id", ondelete="CASCADE"), nullable=False)
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    publish_status = Column(String, nullable=False, default="queued")
    # queued | processing | success | failed | retrying
    retry_count = Column(Integer, nullable=False, default=0)
    meta_publish_id = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

    draft = relationship("PostDraft", back_populates="publish_job")
