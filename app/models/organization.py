from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    owner_email = Column(String, nullable=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    owner = relationship("User", back_populates="owned_organizations")
    accounts = relationship("Account", back_populates="organization", cascade="all, delete-orphan")
    memberships = relationship(
        "OrganizationMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
    )
