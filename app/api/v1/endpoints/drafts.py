from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from app.dependencies import get_db
from app.models.post_draft import PostDraft
from app.models.publish_job import PublishJob
from app.schemas.post_draft import PostDraftCreate, PostDraftUpdate, PostDraftOut, ApprovalAction

router = APIRouter()


@router.get("", response_model=list[PostDraftOut])
async def list_drafts(
    account_id: str | None = None,
    approval_status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(PostDraft)
        .options(selectinload(PostDraft.account))
        .order_by(PostDraft.created_at.desc())
    )
    if account_id:
        query = query.where(PostDraft.account_id == account_id)
    if approval_status:
        query = query.where(PostDraft.approval_status == approval_status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{draft_id}", response_model=PostDraftOut)
async def get_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PostDraft)
        .options(selectinload(PostDraft.account))
        .where(PostDraft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return draft


@router.post("", response_model=PostDraftOut, status_code=201)
async def create_draft(body: PostDraftCreate, db: AsyncSession = Depends(get_db)):
    draft = PostDraft(**body.model_dump())
    db.add(draft)
    await db.commit()
    await db.refresh(draft)
    return draft


@router.patch("/{draft_id}", response_model=PostDraftOut)
async def update_draft(draft_id: str, body: PostDraftUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PostDraft).where(PostDraft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(draft, field, value)
    await db.commit()
    await db.refresh(draft)
    return draft


@router.post("/{draft_id}/approve", response_model=PostDraftOut)
async def approve_draft(draft_id: str, body: ApprovalAction, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PostDraft)
        .options(selectinload(PostDraft.account))
        .where(PostDraft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if body.action == "approve":
        draft.approval_status = "approved"
        # 예약 시각이 있으면 publish_job 생성
        if body.scheduled_at:
            draft.approval_status = "scheduled"
            job = PublishJob(
                post_draft_id=draft.id,
                scheduled_at=body.scheduled_at,
                publish_status="queued",
            )
            db.add(job)
    elif body.action == "reject":
        draft.approval_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    await db.commit()
    await db.refresh(draft)
    return draft


@router.delete("/{draft_id}", status_code=204)
async def delete_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PostDraft).where(PostDraft.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(draft)
    await db.commit()
