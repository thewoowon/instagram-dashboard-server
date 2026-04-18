import secrets
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from app.core.auth import get_current_user
from app.core.config import settings
from app.dependencies import get_db
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.services.email_service import send_invitation_email

router = APIRouter()

VALID_ROLES = {"owner", "admin", "member"}


class MembershipOut(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID | None
    role: str
    invite_email: str | None
    accepted_at: datetime | None
    created_at: datetime
    user_email: str | None = None

    model_config = {"from_attributes": True}


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    slug: str
    role: str  # current user's role in this org
    created_at: datetime


class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "member"


class InviteResponse(BaseModel):
    membership_id: UUID
    invite_url: str
    email_sent: bool


async def _require_org_access(
    db: AsyncSession, user_id: UUID, org_id: UUID, required_roles: set[str]
) -> OrganizationMembership:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.accepted_at.is_not(None),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership or membership.role not in required_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return membership


@router.get("", response_model=list[OrganizationOut])
async def list_my_organizations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
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
    return [
        OrganizationOut(
            id=org.id,
            name=org.name,
            slug=org.slug,
            role=role,
            created_at=org.created_at,
        )
        for org, role in result.all()
    ]


@router.get("/{org_id}/members", response_model=list[MembershipOut])
async def list_members(
    org_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_org_access(db, user.id, UUID(org_id), {"owner", "admin", "member"})
    result = await db.execute(
        select(OrganizationMembership)
        .options(selectinload(OrganizationMembership.user))
        .where(OrganizationMembership.organization_id == org_id)
        .order_by(OrganizationMembership.created_at.asc())
    )
    rows = result.scalars().all()
    return [
        MembershipOut(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            invite_email=m.invite_email,
            accepted_at=m.accepted_at,
            created_at=m.created_at,
            user_email=m.user.email if m.user else None,
        )
        for m in rows
    ]


@router.post("/{org_id}/invites", response_model=InviteResponse, status_code=201)
async def invite_member(
    org_id: str,
    body: InviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.role not in VALID_ROLES or body.role == "owner":
        raise HTTPException(status_code=400, detail="role must be 'admin' or 'member'")

    org_uuid = UUID(org_id)
    actor = await _require_org_access(db, user.id, org_uuid, {"owner", "admin"})

    # Prevent duplicate pending invite for the same email in the same org.
    existing = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_uuid,
            OrganizationMembership.invite_email == body.email,
            OrganizationMembership.accepted_at.is_(None),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 초대된 이메일입니다.")

    # If user with that email already exists and is already a member, also block.
    already = await db.execute(
        select(OrganizationMembership)
        .join(User, User.id == OrganizationMembership.user_id)
        .where(
            OrganizationMembership.organization_id == org_uuid,
            User.email == body.email,
            OrganizationMembership.accepted_at.is_not(None),
        )
    )
    if already.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 멤버입니다.")

    token = secrets.token_urlsafe(32)
    membership = OrganizationMembership(
        organization_id=org_uuid,
        user_id=None,
        role=body.role,
        invite_email=body.email,
        invite_token=token,
        invited_by_user_id=user.id,
    )
    db.add(membership)
    await db.flush()

    org_result = await db.execute(select(Organization).where(Organization.id == org_uuid))
    org = org_result.scalar_one()

    invite_url = f"{settings.APP_URL.rstrip('/')}/accept-invite?token={token}"

    email_sent = False
    try:
        email_sent = await send_invitation_email(
            to_email=body.email,
            org_name=org.name,
            inviter_email=user.email,
            invite_url=invite_url,
        )
    except Exception as e:
        # Keep the invite even if email fails; caller can copy the invite_url manually.
        await db.commit()
        raise HTTPException(status_code=502, detail=f"이메일 발송 실패: {e}")

    await db.commit()
    return InviteResponse(
        membership_id=membership.id,
        invite_url=invite_url,
        email_sent=email_sent,
    )


@router.delete("/{org_id}/members/{membership_id}", status_code=204)
async def remove_member(
    org_id: str,
    membership_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    org_uuid = UUID(org_id)
    actor = await _require_org_access(db, user.id, org_uuid, {"owner", "admin"})

    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.id == membership_id,
            OrganizationMembership.organization_id == org_uuid,
        )
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Membership not found")

    if target.role == "owner":
        raise HTTPException(status_code=400, detail="오너는 제거할 수 없습니다.")
    if actor.role == "admin" and target.role == "admin":
        raise HTTPException(status_code=403, detail="어드민은 다른 어드민을 제거할 수 없습니다.")

    await db.delete(target)
    await db.commit()


class AcceptInviteRequest(BaseModel):
    token: str


class AcceptInviteResponse(BaseModel):
    organization_id: UUID
    organization_name: str
    role: str


# NOTE: mounted under /invitations prefix — see api.py. But since FastAPI routers
# are per-file, keep this under organizations router with a distinct path that
# doesn't clash. We'll expose it as POST /organizations/invitations/accept for simplicity.
@router.post("/invitations/accept", response_model=AcceptInviteResponse)
async def accept_invitation(
    body: AcceptInviteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.invite_token == body.token,
            OrganizationMembership.accepted_at.is_(None),
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=404, detail="Invalid or expired invite")

    # Any logged-in user can accept the link (e.g., forwarded to a different email).
    # Block if that user is already a member of the org.
    dup = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == membership.organization_id,
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.accepted_at.is_not(None),
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="이미 멤버입니다.")

    membership.user_id = user.id
    membership.accepted_at = func.now()
    membership.invite_token = None
    await db.commit()

    org_result = await db.execute(
        select(Organization).where(Organization.id == membership.organization_id)
    )
    org = org_result.scalar_one()
    return AcceptInviteResponse(
        organization_id=org.id,
        organization_name=org.name,
        role=membership.role,
    )
