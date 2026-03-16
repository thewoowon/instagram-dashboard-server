from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.schemas.account import AccountOut


class PostDraftCreate(BaseModel):
    account_id: UUID
    idea_id: Optional[UUID] = None
    format_type: str  # carousel | single | reels_script
    hook: str = ""
    caption: str = ""
    hashtags: list[str] = []
    cta: str = ""
    risk_score: float = 0.0
    quality_score: float = 0.0


class PostDraftUpdate(BaseModel):
    hook: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[list[str]] = None
    cta: Optional[str] = None


class PostDraftOut(BaseModel):
    id: UUID
    account_id: UUID
    idea_id: Optional[UUID]
    format_type: str
    hook: str
    caption: str
    hashtags: list[str]
    cta: str
    risk_score: float
    quality_score: float
    approval_status: str
    created_at: datetime
    updated_at: datetime
    account: Optional[AccountOut] = None

    model_config = {"from_attributes": True}


class ApprovalAction(BaseModel):
    action: str  # approve | reject
    scheduled_at: Optional[datetime] = None  # approve 시 예약 시각
