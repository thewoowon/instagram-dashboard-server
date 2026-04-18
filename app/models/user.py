from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    email = Column(String, nullable=False, unique=True)

    owned_organizations = relationship("Organization", back_populates="owner")
    memberships = relationship(
        "OrganizationMembership",
        foreign_keys="OrganizationMembership.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
