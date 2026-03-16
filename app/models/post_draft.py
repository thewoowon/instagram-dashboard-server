from sqlalchemy import Column, String, Float, ARRAY, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class PostDraft(Base):
    __tablename__ = "post_drafts"

    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    idea_id = Column(UUID(as_uuid=True), ForeignKey("content_ideas.id", ondelete="SET NULL"), nullable=True)
    format_type = Column(String, nullable=False)       # carousel | single | reels_script
    hook = Column(String, nullable=False, default="")
    caption = Column(String, nullable=False, default="")
    hashtags = Column(ARRAY(String), nullable=False, default=list)
    cta = Column(String, nullable=False, default="")
    risk_score = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=0.0)
    approval_status = Column(String, nullable=False, default="pending")
    # pending | approved | rejected | scheduled | published

    account = relationship("Account", back_populates="drafts")
    idea = relationship("ContentIdea", back_populates="drafts")
    creative_assets = relationship("CreativeAsset", back_populates="draft", cascade="all, delete-orphan")
    publish_job = relationship("PublishJob", back_populates="draft", uselist=False, cascade="all, delete-orphan")
    metrics = relationship("PostMetrics", back_populates="draft", cascade="all, delete-orphan")
