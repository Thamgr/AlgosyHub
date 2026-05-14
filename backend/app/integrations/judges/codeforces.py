import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from app.integrations.judges.base import ExternalSubmission, JudgeAdapter, ProblemData
from app.models.enums import SubmissionVerdict

logger = logging.getLogger(__name__)

CF_BASE = "https://codeforces.com"
CF_API = f"{CF_BASE}/api"

# Per-contest cache of problem metadata. The CF API only allows non-admin users
# to call `contest.standings` anonymously with no extra params, so a single call
# returns the full ranklist (multi-MB) — we cache aggressively.
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
    "PARTIAL": SubmissionVerdict.rejected,
    "PRESENTATION_ERROR": SubmissionVerdict.wrong_answer,
    "IDLENESS_LIMIT_EXCEEDED": SubmissionVerdict.time_limit,
    "SECURITY_VIOLATED": SubmissionVerdict.rejected,
    "CRASHED": SubmissionVerdict.runtime_error,
    "INPUT_PREPARATION_CRASHED": SubmissionVerdict.rejected,
    "CHALLENGED": SubmissionVerdict.rejected,
    "SKIPPED": SubmissionVerdict.rejected,
    "FAILED": SubmissionVerdict.rejected,
}


class CodeforcesAdapter(JudgeAdapter):
    """Адаптер Codeforces — работает поверх **публичных** CF endpoints.

    Платформа сама ничего не отправляет на CF: студент сдаёт решение прямо
    у CF (по deep-link `submit_url`), а мы периодически забираем его
    посылки через `/api/user.status` и матчим их с задачами наших контестов.
    """

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 AlgosyHub/0.1"},
        )
        self._contest_cache: dict[int, tuple[float, list[dict[str, Any]]]] = {}
        self._locks: dict[int, asyncio.Lock] = {}
        # Cache for the full problemset (≈ 5MB JSON, rarely changes).
        self._problemset_cache: dict[str, tuple[float, list[ProblemData]]] = {}
        self._problemset_lock = asyncio.Lock()

    def _lock_for(self, contest_id: int) -> asyncio.Lock:
        lock = self._locks.get(contest_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[contest_id] = lock
        return lock

    async def _fetch_contest_problems(self, contest_id: int) -> list[dict[str, Any]]:
        # CF requires this call to be fully anonymous with no extra params,
        # otherwise it returns: "Non-gym contest standings for non-admin users
        # are available only via anonymous GET requests with no extra parameters".
        try:
            resp = await self._http.get(
                f"{CF_API}/contest.standings",
                params={"contestId": contest_id},
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"CF API request failed: {e}") from e

        if resp.status_code != 200:
            raise RuntimeError(f"CF API HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if data.get("status") != "OK":
            raise RuntimeError(f"CF API error: {data.get('comment')}")
        return data["result"]["problems"]

    async def _get_contest_problems(self, contest_id: int) -> list[dict[str, Any]]:
        async with self._lock_for(contest_id):
            cached = self._contest_cache.get(contest_id)
            if cached and time.monotonic() - cached[0] < _CONTEST_TTL:
                return cached[1]

            problems = await self._fetch_contest_problems(contest_id)
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
            external_url=f"{CF_BASE}/problemset/problem/{contest_id}/{index}",
        )

    async def fetch_problemset(
        self, tags: list[str] | None = None
    ) -> list[ProblemData]:
        """Fetch the public CF problemset, optionally filtered by tags.

        CF accepts a semicolon-separated ``tags`` param and returns problems
        whose tag list contains *all* of them. The full payload is ~5MB so
        callers should keep this cached for at least a few minutes.
        """
        cache_key = ";".join(sorted(t.strip() for t in (tags or []) if t.strip()))
        async with self._problemset_lock:
            cached = self._problemset_cache.get(cache_key)
            if cached and time.monotonic() - cached[0] < _CONTEST_TTL:
                return cached[1]

            params: dict[str, str] = {}
            if cache_key:
                params["tags"] = cache_key

            try:
                resp = await self._http.get(
                    f"{CF_API}/problemset.problems", params=params
                )
            except httpx.HTTPError as e:
                raise RuntimeError(f"CF API request failed: {e}") from e

            if resp.status_code != 200:
                raise RuntimeError(
                    f"CF API HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
            if data.get("status") != "OK":
                raise RuntimeError(f"CF API error: {data.get('comment')}")

            out: list[ProblemData] = []
            for p in data["result"]["problems"]:
                contest_id = p.get("contestId")
                index = p.get("index")
                if not contest_id or not index:
                    continue
                out.append(
                    ProblemData(
                        external_id=f"{contest_id}{index}",
                        title=p["name"],
                        tags=list(p.get("tags") or []),
                        difficulty=p.get("rating"),
                        external_url=f"{CF_BASE}/problemset/problem/{contest_id}/{index}",
                    )
                )
            self._problemset_cache[cache_key] = (time.monotonic(), out)
            return out

    def submit_url(self, contest_external_id: str, problem_index: str) -> str | None:
        # На странице /contest/{id}/submit можно предзаполнить выбор задачи
        # параметром submittedProblemIndex (lowercase — так в <option value>).
        return (
            f"{CF_BASE}/contest/{contest_external_id}/submit"
            f"?submittedProblemIndex={problem_index.lower()}"
        )

    async def fetch_user_submissions(
        self, handle: str, count: int = 50
    ) -> list[ExternalSubmission]:
        try:
            resp = await self._http.get(
                f"{CF_API}/user.status",
                params={"handle": handle, "from": 1, "count": count},
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"CF API request failed: {e}") from e

        if resp.status_code != 200:
            raise RuntimeError(f"CF API HTTP {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        if data.get("status") != "OK":
            raise RuntimeError(
                f"CF API error for handle {handle!r}: {data.get('comment')}"
            )

        out: list[ExternalSubmission] = []
        for row in data["result"]:
            problem = row.get("problem") or {}
            contest_id = problem.get("contestId") or row.get("contestId")
            index = problem.get("index")
            if not contest_id or not index:
                continue

            verdict_str = row.get("verdict")
            verdict = (
                SubmissionVerdict.running
                if verdict_str is None
                else CF_VERDICT_MAP.get(verdict_str, SubmissionVerdict.rejected)
            )

            memory_bytes = row.get("memoryConsumedBytes")
            memory_mb = (
                int(memory_bytes / (1024 * 1024)) if memory_bytes else None
            )
            submitted_at = datetime.fromtimestamp(
                int(row.get("creationTimeSeconds") or 0), tz=timezone.utc
            )

            out.append(
                ExternalSubmission(
                    external_id=str(row["id"]),
                    external_problem_id=f"{contest_id}{index}",
                    language=str(row.get("programmingLanguage") or "unknown"),
                    verdict=verdict,
                    time_ms=row.get("timeConsumedMillis"),
                    memory_mb=memory_mb,
                    submitted_at=submitted_at,
                    submission_url=f"{CF_BASE}/contest/{contest_id}/submission/{row['id']}",
                )
            )
        return out
