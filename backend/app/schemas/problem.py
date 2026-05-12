from pydantic import BaseModel

from app.models.enums import ExternalSource


class ProblemResponse(BaseModel):
    id: int
    external_source: ExternalSource
    external_id: str
    title: str
    tags: list[str]
    difficulty: int | None
    time_limit_ms: int | None
    memory_limit_mb: int | None
    cf_url: str

    model_config = {"from_attributes": True}
