from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SubmissionVerdict


class SubmitRequest(BaseModel):
    problem_id: int
    contest_id: int | None = None
    language: str  # e.g. "cpp17", "python3", "pypy3", "java"
    source_code: str


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    problem_id: int
    contest_id: int | None
    language: str
    verdict: SubmissionVerdict
    external_submission_id: str | None
    time_ms: int | None
    memory_mb: int | None
    created_at: datetime

    model_config = {"from_attributes": True}
