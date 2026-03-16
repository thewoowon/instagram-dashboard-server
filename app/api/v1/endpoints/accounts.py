from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db
from app.models.account import Account
from app.schemas.account import AccountOut

router = APIRouter()


@router.get("", response_model=list[AccountOut])
async def list_accounts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.status == "active"))
    return result.scalars().all()


@router.get("/{account_id}", response_model=AccountOut)
async def get_account(account_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Account).where(Account.id == account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account
