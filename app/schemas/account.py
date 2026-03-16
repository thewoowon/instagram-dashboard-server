from pydantic import BaseModel
from typing import Any
from uuid import UUID
from datetime import datetime


class AccountOut(BaseModel):
    id: UUID
    brand_name: str
    instagram_account_id: str
    status: str
    posting_limit_policy: int
    brand_rules_json: dict[str, Any]
    created_at: datetime

    model_config = {"from_attributes": True}
