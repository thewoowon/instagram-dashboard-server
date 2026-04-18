from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.dependencies import get_db
from app.core.auth import get_current_organization
from app.models.account import Account
from app.models.organization import Organization
from app.models.post_draft import PostDraft
from app.models.post_metrics import PostMetrics
from app.models.publish_job import PublishJob
from app.services.insights_service import fetch_media_insights
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


def _org_drafts_query(org_id):
    return (
        select(PostDraft)
        .join(Account, PostDraft.account_id == Account.id)
        .where(Account.org_id == org_id)
    )


@router.get("/overview", response_model=OverviewStats)
async def get_overview(
    account_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    query = _org_drafts_query(org.id)
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
async def get_draft_analytics(
    account_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    """드래프트별 성과 요약."""
    query = (
        _org_drafts_query(org.id)
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


class SyncResult(BaseModel):
    draft_id: UUID
    likes: int
    comments: int
    saves: int
    reach: int
    shares: int


@router.post("/sync/{draft_id}", response_model=SyncResult)
async def sync_draft_insights(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    """Pull fresh Instagram Insights for a published draft and create a new PostMetrics row."""
    result = await db.execute(
        _org_drafts_query(org.id)
        .options(selectinload(PostDraft.account), selectinload(PostDraft.publish_job))
        .where(PostDraft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.approval_status != "published":
        raise HTTPException(status_code=400, detail="아직 발행되지 않은 드래프트입니다.")
    if not draft.publish_job or not draft.publish_job.meta_publish_id:
        raise HTTPException(status_code=400, detail="Instagram media_id가 없습니다.")
    if not draft.account.access_token:
        raise HTTPException(status_code=400, detail="계정 access_token이 없습니다.")

    try:
        snapshot = await fetch_media_insights(
            media_id=draft.publish_job.meta_publish_id,
            access_token=draft.account.access_token,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Insights 조회 실패: {e}")

    metrics = PostMetrics(post_draft_id=draft.id, **snapshot)
    db.add(metrics)
    await db.commit()
    return SyncResult(
        draft_id=draft.id,
        likes=snapshot["likes"],
        comments=snapshot["comments"],
        saves=snapshot["saves"],
        reach=snapshot["reach"],
        shares=snapshot["shares"],
    )
