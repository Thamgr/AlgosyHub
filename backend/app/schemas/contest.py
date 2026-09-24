from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from app.models.enums import ContestStatus, ExternalSource


class ContestTiming(BaseModel):
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime

    @model_validator(mode="after")
    def validate_window(self):
        if self.starts_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("Время окончания должно быть позже времени начала")
        return self


class ContestCreate(ContestTiming):
    title: str
    # Legacy single-group form — still accepted.
    group_id: int | None = None
    # New many-to-many form. If non-empty, takes precedence over ``group_id``.
    group_ids: list[int] = Field(default_factory=list)
    show_ai_hints: bool = True


class ContestResponse(BaseModel):
    id: int
    group_id: int | None
    group_ids: list[int]
    title: str
    status: ContestStatus
    starts_at: datetime | None
    ends_at: datetime | None
    show_ai_hints: bool

    model_config = {"from_attributes": True}


class ContestGroupsUpdate(BaseModel):
    group_ids: list[int] = Field(default_factory=list)


class ContestUpdate(BaseModel):
    """Partial update of contest metadata. Only fields present in the request
    body are touched."""

    title: str | None = None
    show_ai_hints: bool | None = None
    ends_at: AwareDatetime | None = None

    @field_validator("ends_at")
    @classmethod
    def deadline_cannot_be_removed(cls, value):
        if value is None:
            raise ValueError("Укажите дату и время окончания")
        return value


class AddProblemRequest(BaseModel):
    external_source: ExternalSource = ExternalSource.codeforces
    external_id: str  # e.g. "654B"


class ScoreboardCellResponse(BaseModel):
    problem_id: int
    attempts: int
    accepted: bool
    first_accepted_at: datetime | None


class ScoreboardRowResponse(BaseModel):
    user_id: int
    username: str
    solved: int
    attempts_total: int
    cells: list[ScoreboardCellResponse]


class ScoreboardResponse(BaseModel):
    problem_ids: list[int]
    rows: list[ScoreboardRowResponse]


class MatchContestRequest(ContestTiming):
    title: str
    group_ids: list[int] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    rating_min: int | None = None
    rating_max: int | None = None
    count: int = Field(default=5, ge=1, le=15)
    show_ai_hints: bool = True
