from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class ContentIdea(Base):
    __tablename__ = "content_ideas"

    account_id = Column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String, nullable=False)  # trend | backlog | manual | repurpose
    topic = Column(String, nullable=False)
    angle = Column(String, nullable=False, default="")
    priority_score = Column(Float, nullable=False, default=0.0)
    status = Column(String, nullable=False, default="draft")  # draft | in_progress | done

    account = relationship("Account", back_populates="ideas")
    drafts = relationship("PostDraft", back_populates="idea")
