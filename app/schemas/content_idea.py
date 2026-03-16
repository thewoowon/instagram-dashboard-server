from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional


class ContentIdeaCreate(BaseModel):
    account_id: UUID
    source_type: str  # trend | backlog | manual | repurpose
    topic: str
    angle: str = ""
    priority_score: float = 0.0


class ContentIdeaOut(BaseModel):
    id: UUID
    account_id: UUID
    source_type: str
    topic: str
    angle: str
    priority_score: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
