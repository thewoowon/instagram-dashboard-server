from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nullable: pending invites exist before the invitee has a user row.
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    role = Column(String, nullable=False, default="member")  # owner | admin | member
    invite_email = Column(String, nullable=True)
    invite_token = Column(String, nullable=True, unique=True)
    invited_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", foreign_keys=[user_id], back_populates="memberships")
