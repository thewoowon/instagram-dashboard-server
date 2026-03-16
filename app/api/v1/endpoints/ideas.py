from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.dependencies import get_db
from app.models.content_idea import ContentIdea
from app.schemas.content_idea import ContentIdeaCreate, ContentIdeaOut

router = APIRouter()


@router.get("", response_model=list[ContentIdeaOut])
async def list_ideas(
    account_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(ContentIdea).order_by(ContentIdea.priority_score.desc())
    if account_id:
        query = query.where(ContentIdea.account_id == account_id)
    if status:
        query = query.where(ContentIdea.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ContentIdeaOut, status_code=201)
async def create_idea(body: ContentIdeaCreate, db: AsyncSession = Depends(get_db)):
    idea = ContentIdea(**body.model_dump())
    db.add(idea)
    await db.commit()
    await db.refresh(idea)
    return idea


@router.patch("/{idea_id}/status", response_model=ContentIdeaOut)
async def update_idea_status(idea_id: str, status: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContentIdea).where(ContentIdea.id == idea_id))
    idea = result.scalar_one_or_none()
    if not idea:
        raise HTTPException(status_code=404, detail="Idea not found")
    idea.status = status
    await db.commit()
    await db.refresh(idea)
    return idea
