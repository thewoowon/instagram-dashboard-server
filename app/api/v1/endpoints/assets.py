import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from PIL import Image, UnidentifiedImageError
from app.dependencies import get_db
from app.core.auth import get_current_organization
from app.models.account import Account
from app.models.organization import Organization
from app.models.post_draft import PostDraft
from app.models.creative_asset import CreativeAsset
from app.services.storage_service import upload_to_storage

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/gif", "video/mp4",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MIN_IMAGE_DIMENSION = 320  # Instagram requires ≥320px on shorter side


class AssetOut(BaseModel):
    id: UUID
    post_draft_id: UUID
    asset_type: str
    storage_url: str
    prompt: str
    preview_url: str
    created_at: datetime

    model_config = {"from_attributes": True}


async def _get_org_draft(db: AsyncSession, draft_id: str, org_id) -> PostDraft | None:
    result = await db.execute(
        select(PostDraft)
        .join(Account, PostDraft.account_id == Account.id)
        .where(PostDraft.id == draft_id, Account.org_id == org_id)
    )
    return result.scalar_one_or_none()


@router.post("/{draft_id}/assets", response_model=AssetOut, status_code=201)
async def upload_asset(
    draft_id: str,
    file: UploadFile = File(...),
    asset_type: str = Form("image"),
    prompt: str = Form(""),
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    """드래프트에 이미지/비디오 asset 업로드."""
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    if file.content_type and file.content_type.startswith("image/"):
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
        except (UnidentifiedImageError, OSError):
            raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")
        if min(width, height) < MIN_IMAGE_DIMENSION:
            raise HTTPException(
                status_code=400,
                detail=f"이미지 해상도가 너무 작습니다 ({width}x{height}). 짧은 변이 {MIN_IMAGE_DIMENSION}px 이상이어야 합니다.",
            )

    try:
        storage_url = await upload_to_storage(
            file_bytes=file_bytes,
            filename=file.filename or "upload",
            content_type=file.content_type,
            folder=f"drafts/{draft_id}",
        )
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    asset = CreativeAsset(
        post_draft_id=draft.id,
        asset_type=asset_type,
        storage_url=storage_url,
        prompt=prompt,
        preview_url=storage_url,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


@router.get("/{draft_id}/assets", response_model=list[AssetOut])
async def list_assets(
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    result = await db.execute(
        select(CreativeAsset).where(CreativeAsset.post_draft_id == draft_id)
    )
    return result.scalars().all()


@router.delete("/{draft_id}/assets/{asset_id}", status_code=204)
async def delete_asset(
    draft_id: str,
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    org: Organization = Depends(get_current_organization),
):
    draft = await _get_org_draft(db, draft_id, org.id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    result = await db.execute(
        select(CreativeAsset).where(
            CreativeAsset.id == asset_id,
            CreativeAsset.post_draft_id == draft_id,
        )
    )
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    await db.delete(asset)
    await db.commit()
