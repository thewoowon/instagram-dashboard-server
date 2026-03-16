from sqlalchemy import Column, String, Integer, JSON
from sqlalchemy.orm import relationship
from app.db.base import Base


class Account(Base):
    __tablename__ = "accounts"

    brand_name = Column(String, nullable=False)        # 'mistakr' | '100:0lab'
    instagram_account_id = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, default="active")  # active | inactive
    posting_limit_policy = Column(Integer, nullable=False, default=25)
    brand_rules_json = Column(JSON, nullable=False, default=dict)

    ideas = relationship("ContentIdea", back_populates="account", cascade="all, delete-orphan")
    drafts = relationship("PostDraft", back_populates="account", cascade="all, delete-orphan")
