import asyncio
import re
import time
from typing import Any

import codeforcespy.errors
import codeforcespy.processors
import httpx

from app.integrations.judges.base import JudgeAdapter, ProblemData, SubmissionResult
from app.models.enums import SubmissionVerdict

CF_API = "https://codeforces.com/api"

# Per-contest cache of problem metadata. With auth, each call is ~few KB; without
# auth CF only allows param-less `contest.standings`, which can be multi-MB.
_CONTEST_TTL = 30 * 60  # 30 minutes


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
    def __init__(
        self,
        account: str = "",
        password: str = "",
        api_key: str = "",
        api_secret: str = "",
    ) -> None:
        self.account = account
        self.password = password
        self._api_key = api_key
        self._api_secret = api_secret

        self._authed = bool(api_key and api_secret)
        if self._authed:
            self._client: codeforcespy.processors.AsyncMethod | None = (
                codeforcespy.processors.AsyncMethod(
                    enable_auth=True,
                    auth_key=api_key,
                    secret=api_secret,
                )
            )
            self._fallback_http: httpx.AsyncClient | None = None
        else:
            self._client = None
            self._fallback_http = httpx.AsyncClient(timeout=30)

        self._contest_cache: dict[int, tuple[float, list[dict[str, Any]]]] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, contest_id: int) -> asyncio.Lock:
        lock = self._locks.get(contest_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[contest_id] = lock
        return lock

    async def _fetch_contest_problems_authed(self, contest_id: int) -> list[dict[str, Any]]:
        assert self._client is not None
        try:
            standings_list = await self._client.get_contest_standings(
                contest_id=contest_id,
                from_index=1,
                count=1,
                show_unofficial=False,
            )
        except codeforcespy.errors.APIError as e:
            raise RuntimeError(f"CF API error: {e}") from e

        if not standings_list:
            raise RuntimeError("CF API returned empty standings")

        standings = standings_list[0]
        raw_problems = standings.problems
        if raw_problems is None:
            return []
        if not isinstance(raw_problems, list):
            raw_problems = [raw_problems]

        return [
            {
                "index": p.index,
                "name": p.name,
                "tags": list(p.tags or []),
                "rating": p.rating,
            }
            for p in raw_problems
        ]

    async def _fetch_contest_problems_anon(self, contest_id: int) -> list[dict[str, Any]]:
        # Without API key, CF only allows `contest.standings?contestId=X` with no other
        # params — response includes full ranklist, which we discard.
        assert self._fallback_http is not None
        resp = await self._fallback_http.get(
            f"{CF_API}/contest.standings",
            params={"contestId": contest_id},
        )
        resp.raise_for_status()
        data = resp.json()
        if data["status"] != "OK":
            raise RuntimeError(f"CF API error: {data.get('comment')}")
        return data["result"]["problems"]

    async def _get_contest_problems(self, contest_id: int) -> list[dict[str, Any]]:
        async with self._lock_for(contest_id):
            cached = self._contest_cache.get(contest_id)
            if cached and time.monotonic() - cached[0] < _CONTEST_TTL:
                return cached[1]

            if self._authed:
                problems = await self._fetch_contest_problems_authed(contest_id)
            else:
                problems = await self._fetch_contest_problems_anon(contest_id)

            self._contest_cache[contest_id] = (time.monotonic(), problems)
            return problems

    async def fetch_problem(self, external_id: str) -> ProblemData:
        contest_id, index = _parse_external_id(external_id)
        problems = await self._get_contest_problems(contest_id)

        match = next((p for p in problems if p["index"] == index), None)
        if match is None:
            raise ValueError(f"Problem {external_id} not found on Codeforces")

        return ProblemData(
            external_id=f"{contest_id}{index}",
            title=match["name"],
            tags=list(match.get("tags") or []),
            difficulty=match.get("rating"),
            external_url=f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
        )

    async def submit(self, external_id: str, language: str, source_code: str) -> str:
        raise NotImplementedError("Submit not implemented yet")

    async def poll_verdict(self, external_submission_id: str) -> SubmissionResult:
        raise NotImplementedError("Polling not implemented yet")
