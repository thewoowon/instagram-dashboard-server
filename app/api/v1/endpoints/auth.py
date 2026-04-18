from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from app.core.auth import get_current_user
from app.dependencies import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership


router = APIRouter()


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str
    created_at: datetime
    model_config = {"from_attributes": True}


class MeOut(BaseModel):
    id: UUID
    email: str
    created_at: datetime
    organizations: list[OrganizationOut]
    model_config = {"from_attributes": True}


@router.get("/me", response_model=MeOut)
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Organization.id,
        )
        .where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.accepted_at.is_not(None),
        )
        .order_by(Organization.created_at.asc())
    )
    rows = result.all()
    return MeOut(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        organizations=[
            OrganizationOut(
                id=o.id,
                name=o.name,
                slug=o.slug,
                role=role,
                created_at=o.created_at,
            )
            for o, role in rows
        ],
    )
