from datetime import datetime

from pydantic import BaseModel

from app.models.enums import ContestStatus, ExternalSource
from app.schemas.problem import ProblemResponse


class ContestCreate(BaseModel):
    title: str
    group_id: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class ContestResponse(BaseModel):
    id: int
    group_id: int | None
    title: str
    status: ContestStatus
    starts_at: datetime | None
    ends_at: datetime | None

    model_config = {"from_attributes": True}


class AddProblemRequest(BaseModel):
    external_source: ExternalSource = ExternalSource.codeforces
    external_id: str  # e.g. "654B"
