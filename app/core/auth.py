import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func
from uuid import UUID

from app.core.config import settings
from app.dependencies import get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.SUPABASE_URL:
            raise RuntimeError("SUPABASE_URL not configured")
        _jwks_client = PyJWKClient(f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json")
    return _jwks_client


async def get_current_user(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = _get_jwks_client().get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        import logging
        logging.getLogger(__name__).warning(f"JWT decode failed: {e} | token_prefix={token[:30]}...")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    sub = payload.get("sub")
    email = payload.get("email")
    if not sub or not email:
        raise HTTPException(status_code=401, detail="Token missing sub or email")

    user_id = UUID(sub)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(id=user_id, email=email)
        db.add(user)
        await db.flush()

        # 같은 이메일로 미리 만들어둔 org가 있으면 소유권 연결, 없으면 새 org 생성
        existing = await db.execute(
            select(Organization).where(
                Organization.owner_email == email,
                Organization.owner_user_id.is_(None),
            )
        )
        claimed = existing.scalar_one_or_none()
        if claimed:
            claimed.owner_user_id = user_id
            # Also ensure an owner membership exists.
            db.add(OrganizationMembership(
                organization_id=claimed.id,
                user_id=user_id,
                role="owner",
                accepted_at=func.now(),
            ))
        else:
            new_org = Organization(
                name=_default_org_name(email),
                slug=_default_org_slug(user_id),
                owner_email=email,
                owner_user_id=user_id,
            )
            db.add(new_org)
            await db.flush()
            db.add(OrganizationMembership(
                organization_id=new_org.id,
                user_id=user_id,
                role="owner",
                accepted_at=func.now(),
            ))

        # Auto-accept any pending invitations addressed to this email.
        await db.execute(
            update(OrganizationMembership)
            .where(
                OrganizationMembership.user_id.is_(None),
                OrganizationMembership.invite_email == email,
            )
            .values(user_id=user_id, accepted_at=func.now(), invite_token=None)
        )

        await db.commit()
        await db.refresh(user)

    return user


async def get_current_organization(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
) -> Organization:
    """Resolve the active organization for this request.

    If the client sends an X-Org-Id header, verify the user has an accepted
    membership in that org. Otherwise, pick any accepted membership (owner preferred)
    so existing single-org users keep working.
    """
    q = (
        select(Organization)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Organization.id,
        )
        .where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.accepted_at.is_not(None),
        )
    )

    if x_org_id:
        try:
            target_id = UUID(x_org_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid X-Org-Id")
        q = q.where(Organization.id == target_id)
        result = await db.execute(q)
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=403, detail="No access to this organization")
        return org

    q = q.order_by(
        (OrganizationMembership.role == "owner").desc(),
        OrganizationMembership.created_at.asc(),
    )
    result = await db.execute(q)
    org = result.scalars().first()
    if not org:
        raise HTTPException(status_code=404, detail="No organization for user")
    return org


def _default_org_name(email: str) -> str:
    local = email.split("@", 1)[0]
    return f"{local} Workspace"


def _default_org_slug(user_id: UUID) -> str:
    return f"org-{user_id.hex[:12]}"
