from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.dependencies import get_db
from app.models.post_draft import PostDraft
from app.models.post_metrics import PostMetrics
from app.models.publish_job import PublishJob
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

router = APIRouter()


class DraftSummary(BaseModel):
    id: UUID
    hook: str
    format_type: str
    approval_status: str
    quality_score: float
    risk_score: float
    created_at: datetime
    likes: int = 0
    comments: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0

    model_config = {"from_attributes": True}


class OverviewStats(BaseModel):
    total_drafts: int
    pending: int
    approved: int
    published: int
    rejected: int
    avg_quality_score: float
    avg_risk_score: float


@router.get("/overview", response_model=OverviewStats)
async def get_overview(account_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    query = select(PostDraft)
    if account_id:
        query = query.where(PostDraft.account_id == account_id)
    result = await db.execute(query)
    drafts = result.scalars().all()

    if not drafts:
        return OverviewStats(
            total_drafts=0, pending=0, approved=0, published=0, rejected=0,
            avg_quality_score=0, avg_risk_score=0
        )

    return OverviewStats(
        total_drafts=len(drafts),
        pending=sum(1 for d in drafts if d.approval_status == "pending"),
        approved=sum(1 for d in drafts if d.approval_status == "approved"),
        published=sum(1 for d in drafts if d.approval_status == "published"),
        rejected=sum(1 for d in drafts if d.approval_status == "rejected"),
        avg_quality_score=round(sum(d.quality_score for d in drafts) / len(drafts), 1),
        avg_risk_score=round(sum(d.risk_score for d in drafts) / len(drafts), 1),
    )


@router.get("/drafts", response_model=list[DraftSummary])
async def get_draft_analytics(account_id: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """드래프트별 성과 요약 (발행된 것 위주)."""
    from sqlalchemy.orm import selectinload
    query = (
        select(PostDraft)
        .options(selectinload(PostDraft.metrics))
        .order_by(PostDraft.created_at.desc())
    )
    if account_id:
        query = query.where(PostDraft.account_id == account_id)
    result = await db.execute(query)
    drafts = result.scalars().all()

    summaries = []
    for d in drafts:
        latest_metrics = sorted(d.metrics or [], key=lambda m: m.collected_at, reverse=True)
        m = latest_metrics[0] if latest_metrics else None
        summaries.append(DraftSummary(
            id=d.id,
            hook=d.hook,
            format_type=d.format_type,
            approval_status=d.approval_status,
            quality_score=d.quality_score,
            risk_score=d.risk_score,
            created_at=d.created_at,
            likes=m.likes if m else 0,
            comments=m.comments if m else 0,
            saves=m.saves if m else 0,
            reach=m.reach if m else 0,
            impressions=m.impressions if m else 0,
        ))
    return summaries
