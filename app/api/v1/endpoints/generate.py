from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.dependencies import get_db
from app.models.account import Account
from app.models.post_draft import PostDraft
from app.models.content_idea import ContentIdea
from app.services.generate_service import generate_draft_content, generate_ideas
from app.schemas.post_draft import PostDraftOut
from app.schemas.content_idea import ContentIdeaOut
from sqlalchemy.orm import selectinload

router = APIRouter()


class GenerateDraftRequest(BaseModel):
    account_id: str
    topic: str
    angle: str = ""
    format_type: str = "carousel"  # carousel | single | reels_script
    idea_id: str | None = None


class GenerateIdeasRequest(BaseModel):
    account_id: str
    count: int = 5


@router.post("/draft", response_model=PostDraftOut, status_code=201)
async def generate_draft(body: GenerateDraftRequest, db: AsyncSession = Depends(get_db)):
    """AI로 드래프트 생성 후 DB 저장."""
    # 계정 조회
    result = await db.execute(select(Account).where(Account.id == body.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # GPT 생성
    try:
        generated = await generate_draft_content(
            brand_name=account.brand_name,
            topic=body.topic,
            angle=body.angle,
            format_type=body.format_type,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    # DB 저장
    draft = PostDraft(
        account_id=account.id,
        idea_id=body.idea_id,
        format_type=body.format_type,
        hook=generated.get("hook", ""),
        caption=generated.get("caption", ""),
        hashtags=generated.get("hashtags", []),
        cta=generated.get("cta", ""),
        risk_score=float(generated.get("risk_score", 0)),
        quality_score=float(generated.get("quality_score", 0)),
        approval_status="pending",
    )
    db.add(draft)
    await db.commit()

    # idea 상태 업데이트
    if body.idea_id:
        idea_result = await db.execute(select(ContentIdea).where(ContentIdea.id == body.idea_id))
        idea = idea_result.scalar_one_or_none()
        if idea:
            idea.status = "in_progress"
            await db.commit()

    # account 포함해서 반환
    await db.refresh(draft)
    result2 = await db.execute(
        select(PostDraft)
        .options(selectinload(PostDraft.account))
        .where(PostDraft.id == draft.id)
    )
    return result2.scalar_one()


@router.post("/ideas", response_model=list[ContentIdeaOut], status_code=201)
async def generate_ideas_endpoint(body: GenerateIdeasRequest, db: AsyncSession = Depends(get_db)):
    """AI로 아이디어 후보 생성 후 DB 저장."""
    result = await db.execute(select(Account).where(Account.id == body.account_id))
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    try:
        ideas_data = await generate_ideas(brand_name=account.brand_name, count=body.count)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

    saved = []
    for item in ideas_data:
        idea = ContentIdea(
            account_id=account.id,
            source_type="trend",
            topic=item.get("topic", ""),
            angle=item.get("angle", ""),
            priority_score=float(item.get("priority_score", 0)),
            status="draft",
        )
        db.add(idea)
        saved.append(idea)

    await db.commit()
    for idea in saved:
        await db.refresh(idea)

    return saved
