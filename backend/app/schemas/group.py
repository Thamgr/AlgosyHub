from pydantic import BaseModel

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


class GroupScoreboardContest(BaseModel):
    id: int
    title: str
    problems: list[ProblemResponse]


class GroupScoreboardCell(ScoreboardCellResponse):
    contest_id: int


class GroupScoreboardRow(BaseModel):
    user_id: int
    username: str
    solved: int
    attempts_total: int
    # Sparse: absent contest/problem pairs mean no submissions.
    cells: list[GroupScoreboardCell]


class GroupScoreboardResponse(BaseModel):
    contests: list[GroupScoreboardContest]
    rows: list[GroupScoreboardRow]
