from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.dependencies import get_db
from app.core.auth import get_current_organization
from app.models.account import Account
from app.models.organization import Organization
from app.models.post_draft import PostDraft
from app.models.publish_job import PublishJob
from app.models.post_metrics import PostMetrics
from app.schemas.post_draft import PostDraftCreate, PostDraftUpdate, PostDraftOut, ApprovalAction
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


def _base_draft_query(org_id):
    return (
        select(PostDraft)
        .join(Account, PostDraft.account_id == Account.id)
        .where(Account.org_id == org_id)
        .options(selectinload(PostDraft.account), selectinload(PostDraft.creative_assets))
    )


async def _get_org_draft(db: AsyncSession, draft_id: str, org_id) -> PostDraft | None:
    result = await db.execute(_base_draft_query(org_id).where(PostDraft.id == draft_id))
    return result.scalar_one_or_none()


@router.get("", response_model=list[PostDraftOut])
async def list_drafts(
    account_id: str | None = None,
    approval_status: str | None = None,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    query = _base_draft_query(org.id).order_by(PostDraft.created_at.desc())
    if account_id:
        query = query.where(PostDraft.account_id == account_id)
    if approval_status:
        query = query.where(PostDraft.approval_status == approval_status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{draft_id}", response_model=PostDraftOut)
async def get_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("", response_model=PostDraftOut, status_code=201)
async def create_draft(
    body: PostDraftCreate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    # account가 내 org 소속인지 검증
    acc_result = await db.execute(
        select(Account).where(Account.id == body.account_id, Account.org_id == org.id)
    )
    if not acc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")

    draft = PostDraft(**body.model_dump())
    db.add(draft)
    await db.commit()
    return await _get_org_draft(db, draft.id, org.id)


@router.patch("/{draft_id}", response_model=PostDraftOut)
async def update_draft(
    draft_id: str,
    body: PostDraftUpdate,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(draft, field, value)
    await db.commit()
    return await _get_org_draft(db, draft_id, org.id)


@router.post("/{draft_id}/approve", response_model=PostDraftOut)
async def approve_draft(
    draft_id: str,
    body: ApprovalAction,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if body.action == "approve":
        draft.approval_status = "approved"
        if body.scheduled_at:
            draft.approval_status = "scheduled"
            db.add(PublishJob(
                post_draft_id=draft.id,
                scheduled_at=body.scheduled_at,
                publish_status="queued",
            ))
    elif body.action == "reject":
        draft.approval_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    await db.commit()
    await db.refresh(draft)
    return draft


@router.post("/{draft_id}/publish", response_model=PostDraftOut)
async def publish_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    """즉시 Instagram에 발행."""
    from app.services.instagram_service import publish_to_instagram

    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    image_assets = [a for a in (draft.creative_assets or []) if a.asset_type == "image"]
    if not image_assets:
        raise HTTPException(status_code=400, detail="발행할 이미지가 없습니다.")

    if not draft.account.access_token:
        raise HTTPException(status_code=400, detail=f"{draft.account.brand_name} 계정에 access_token이 설정되지 않았습니다.")

    image_urls = (
        [image_assets[0].storage_url]
        if draft.format_type == "single"
        else [a.storage_url for a in image_assets]
    )

    caption_text = (
        f"{draft.hook}\n\n{draft.caption}\n\n{draft.cta}\n\n"
        + " ".join(f"#{tag}" for tag in (draft.hashtags or []))
    )

    try:
        media_id = await publish_to_instagram(
            image_urls=image_urls,
            caption=caption_text,
            access_token=draft.account.access_token,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    draft.approval_status = "published"
    db.add(PublishJob(
        post_draft_id=draft.id,
        scheduled_at=datetime.utcnow(),
        publish_status="published",
        meta_publish_id=media_id,
    ))

    # Best-effort initial insights snapshot. Newly-published media usually returns zeros —
    # that's fine; manual refresh on /analytics pulls updated numbers.
    try:
        from app.services.insights_service import fetch_media_insights
        snapshot = await fetch_media_insights(media_id, draft.account.access_token)
        db.add(PostMetrics(post_draft_id=draft.id, **snapshot))
    except Exception as e:
        logger.warning(f"initial insights snapshot failed for draft={draft.id}: {e}")

    await db.commit()
    await db.refresh(draft)
    return draft


@router.delete("/{draft_id}", status_code=204)
async def delete_draft(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(draft)
    await db.commit()
