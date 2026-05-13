from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ExternalSource


class JudgeAccountResponse(BaseModel):
    source: ExternalSource
    handle: str
    updated_at: datetime

    model_config = {"from_attributes": True}


class JudgeAccountUpsert(BaseModel):
    handle: str = Field(min_length=1, max_length=100)
