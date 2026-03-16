from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class PostMetrics(Base):
    __tablename__ = "post_metrics"

    post_draft_id = Column(UUID(as_uuid=True), ForeignKey("post_drafts.id", ondelete="CASCADE"), nullable=False)
    impressions = Column(Integer, nullable=False, default=0)
    reach = Column(Integer, nullable=False, default=0)
    likes = Column(Integer, nullable=False, default=0)
    comments = Column(Integer, nullable=False, default=0)
    saves = Column(Integer, nullable=False, default=0)
    shares = Column(Integer, nullable=False, default=0)
    profile_visits = Column(Integer, nullable=False, default=0)
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    draft = relationship("PostDraft", back_populates="metrics")
