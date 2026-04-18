from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db
from app.core.auth import get_current_organization
from app.models.account import Account
from app.models.organization import Organization
from app.schemas.account import AccountOut, AccountUpdate

router = APIRouter()


@router.get("", response_model=list[AccountOut])
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    result = await db.execute(
        select(Account).where(Account.org_id == org.id, Account.status == "active")
    )
    return result.scalars().all()


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.org_id == org.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.patch("/{account_id}", response_model=AccountOut)
async def update_account(
    account_id: str,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    result = await db.execute(
        select(Account).where(Account.id == account_id, Account.org_id == org.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(account, field, value)
    await db.commit()
    await db.refresh(account)
    return account
