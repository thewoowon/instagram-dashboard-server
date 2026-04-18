from pydantic import BaseModel, Field, computed_field
from typing import Any, Optional
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
    access_token: Optional[str] = Field(default=None, exclude=True)

    @computed_field
    @property
    def has_access_token(self) -> bool:
        return bool(self.access_token)

    model_config = {"from_attributes": True}


class AccountUpdate(BaseModel):
    access_token: Optional[str] = None
    status: Optional[str] = None
    posting_limit_policy: Optional[int] = None
    brand_rules_json: Optional[dict[str, Any]] = None
