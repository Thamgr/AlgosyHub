from pydantic import BaseModel, ConfigDict, Field

from app.schemas.auth import UserResponse
from app.schemas.contest import ScoreboardCellResponse
from app.schemas.problem import ProblemResponse


class GroupCreate(BaseModel):
    name: str
    description: str | None = None


class GroupResponse(BaseModel):
    id: int
    teacher_id: int
    name: str
    description: str | None

    model_config = {"from_attributes": True}


class GroupAuthorResponse(BaseModel):
    id: int
    username: str
    full_name: str
    avatar_emoji: str

    model_config = {"from_attributes": True}


class GroupDetailResponse(GroupResponse):
    author: GroupAuthorResponse


class GroupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)


class GroupSettingsResponse(BaseModel):
    group: GroupResponse
    members: list[UserResponse]
    observers: list[UserResponse]


class GroupScoreboardContest(BaseModel):
    id: int
    title: str
    problems: list[ProblemResponse]


class GroupScoreboardCell(ScoreboardCellResponse):
    contest_id: int


class GroupScoreboardRow(BaseModel):
    user_id: int
    username: str
    full_name: str = ""
    avatar_emoji: str = ""
    solved: int
    attempts_total: int
    # Sparse: absent contest/problem pairs mean no submissions.
    cells: list[GroupScoreboardCell]


class GroupScoreboardResponse(BaseModel):
    contests: list[GroupScoreboardContest]
    rows: list[GroupScoreboardRow]
