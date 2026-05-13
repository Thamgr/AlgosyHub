import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx

from app.models.enums import SubmissionVerdict

if TYPE_CHECKING:
    from app.models.problem import Problem


@dataclass
class ProblemData:
    external_id: str
    title: str
    external_url: str
    tags: list[str] = field(default_factory=list)
    difficulty: int | None = None


@dataclass
class SubmissionResult:
    verdict: SubmissionVerdict
    time_ms: int | None = None
    memory_mb: int | None = None


_HEAD_RE = re.compile(r"<head([^>]*)>", re.IGNORECASE)


def _inject_base(html: str, base_url: str) -> str:
    """Inject <base href> into <head> so relative URLs in the page resolve against the judge."""
    tag = f'<base href="{base_url}">'
    if _HEAD_RE.search(html):
        return _HEAD_RE.sub(lambda m: m.group(0) + tag, html, count=1)
    return tag + html


class JudgeAdapter(ABC):
    @abstractmethod
    async def fetch_problem(self, external_id: str) -> ProblemData: ...

    @abstractmethod
    async def submit(self, external_id: str, language: str, source_code: str) -> str: ...

    @abstractmethod
    async def poll_verdict(self, external_submission_id: str) -> SubmissionResult: ...

    async def render_statement_html(self, problem: "Problem") -> str:
        """Return a full HTML page with the problem statement, to be served in a new tab.

        Default implementation: GET ``problem.external_url`` and inject a ``<base href>``
        pointing at the judge's host so CSS/JS/images/math resolve correctly.
        Override per-judge when the statement isn't directly served as HTML
        (e.g. LeetCode renders content via JS — would need their GraphQL API).
        """
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(
                problem.external_url,
                headers={"User-Agent": "Mozilla/5.0 AlgosyHub/0.1"},
            )
        resp.raise_for_status()

        parsed = urlparse(problem.external_url)
        base = f"{parsed.scheme}://{parsed.netloc}/"
        return _inject_base(resp.text, base)
