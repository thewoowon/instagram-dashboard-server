from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class CreativeAsset(Base):
    __tablename__ = "creative_assets"

    post_draft_id = Column(UUID(as_uuid=True), ForeignKey("post_drafts.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String, nullable=False)   # image | video | thumbnail
    storage_url = Column(String, nullable=False)
    prompt = Column(String, nullable=False, default="")
    preview_url = Column(String, nullable=False, default="")

    draft = relationship("PostDraft", back_populates="creative_assets")
