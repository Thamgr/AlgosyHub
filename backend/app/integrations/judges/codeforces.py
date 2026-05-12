import re

import httpx

from app.integrations.judges.base import JudgeAdapter, ProblemData, SubmissionResult
from app.models.enums import SubmissionVerdict

CF_API = "https://codeforces.com/api"

# Seconds between CF API calls (CF limit: 5 req/s)
_RATE_DELAY = 0.25


def _parse_external_id(external_id: str) -> tuple[int, str]:
    """'654B' → (654, 'B')"""
    m = re.match(r"^(\d+)([A-Z]\d*)$", external_id.upper())
    if not m:
        raise ValueError(f"Invalid CF problem id: {external_id!r}. Expected format: 654B")
    return int(m.group(1)), m.group(2)


CF_VERDICT_MAP = {
    "OK": SubmissionVerdict.accepted,
    "WRONG_ANSWER": SubmissionVerdict.wrong_answer,
    "TIME_LIMIT_EXCEEDED": SubmissionVerdict.time_limit,
    "MEMORY_LIMIT_EXCEEDED": SubmissionVerdict.memory_limit,
    "RUNTIME_ERROR": SubmissionVerdict.runtime_error,
    "COMPILATION_ERROR": SubmissionVerdict.compilation_error,
    "REJECTED": SubmissionVerdict.rejected,
    "TESTING": SubmissionVerdict.running,
}


class CodeforcesAdapter(JudgeAdapter):
    def __init__(self, account: str = "", password: str = "") -> None:
        self.account = account
        self.password = password
        self._client = httpx.AsyncClient(timeout=15)

    async def fetch_problem(self, external_id: str) -> ProblemData:
        contest_id, index = _parse_external_id(external_id)

        resp = await self._client.get(
            f"{CF_API}/contest.standings",
            params={"contestId": contest_id, "from": 1, "count": 1, "showUnofficial": "false"},
        )
        resp.raise_for_status()
        data = resp.json()

        if data["status"] != "OK":
            raise RuntimeError(f"CF API error: {data.get('comment')}")

        problems: list[dict] = data["result"]["problems"]
        match = next((p for p in problems if p["index"] == index), None)
        if match is None:
            raise ValueError(f"Problem {external_id} not found on Codeforces")

        return ProblemData(
            external_id=external_id.upper(),
            title=match["name"],
            tags=match.get("tags", []),
            difficulty=match.get("rating"),
            cf_url=f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
        )

    async def submit(self, external_id: str, language: str, source_code: str) -> str:
        raise NotImplementedError("Submit not implemented yet")

    async def poll_verdict(self, external_submission_id: str) -> SubmissionResult:
        raise NotImplementedError("Polling not implemented yet")
