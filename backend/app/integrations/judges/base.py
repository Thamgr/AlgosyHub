from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models.enums import SubmissionVerdict


@dataclass
class ProblemData:
    external_id: str
    title: str
    cf_url: str
    tags: list[str] = field(default_factory=list)
    difficulty: int | None = None
    time_limit_ms: int | None = None
    memory_limit_mb: int | None = None


@dataclass
class SubmissionResult:
    verdict: SubmissionVerdict
    time_ms: int | None = None
    memory_mb: int | None = None


class JudgeAdapter(ABC):
    @abstractmethod
    async def fetch_problem(self, external_id: str) -> ProblemData: ...

    @abstractmethod
    async def submit(self, external_id: str, language: str, source_code: str) -> str: ...

    @abstractmethod
    async def poll_verdict(self, external_submission_id: str) -> SubmissionResult: ...
