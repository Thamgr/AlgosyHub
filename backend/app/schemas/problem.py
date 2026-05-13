from pydantic import BaseModel

from app.models.enums import ExternalSource


class ProblemResponse(BaseModel):
    id: int
    external_source: ExternalSource
    external_id: str
    title: str
    tags: list[str]
    difficulty: int | None
    external_url: str

    model_config = {"from_attributes": True}
