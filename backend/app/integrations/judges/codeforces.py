import asyncio
import logging
import random
import re
import secrets
import string
import time
from typing import Any

import codeforcespy.processors
import httpx

from app.integrations.judges.base import JudgeAdapter, ProblemData, SubmissionResult
from app.models.enums import SubmissionVerdict

logger = logging.getLogger(__name__)

CF_BASE = "https://codeforces.com"
CF_API = f"{CF_BASE}/api"

# Per-contest cache of problem metadata. The CF API only allows non-admin users
# to call `contest.standings` anonymously with no extra params, so a single call
# returns the full ranklist (multi-MB) — we cache aggressively.
_CONTEST_TTL = 30 * 60  # 30 minutes

# Codeforces web language IDs. The set is fairly stable but CF rotates them
# from time to time; the values below come from the live "Submit" page.
CF_LANGUAGE_IDS: dict[str, int] = {
    "cpp17": 89,    # GNU G++17 7.3.0
    "cpp20": 91,    # GNU G++20 13.2 (64 bit, winlibs)
    "cpp": 89,      # alias → C++17
    "python3": 31,  # Python 3.8.10
    "python": 31,
    "pypy3": 70,    # PyPy 3.10 (7.3.15, 64bit)
    "pypy": 70,
    "java": 87,     # Java 17 64bit
    "kotlin": 88,   # Kotlin 1.9.21
    "go": 32,       # Go 1.22.2
    "rust": 75,     # Rust 1.75.0
    "csharp": 79,   # C# 10, .NET SDK 6.0
}

DEFAULT_LANGUAGE = "cpp17"


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


_CSRF_RE = re.compile(
    r'name=["\']X-Csrf-Token["\']\s+content=["\']([0-9a-f]+)["\']', re.IGNORECASE
)
_CSRF_INPUT_RE = re.compile(
    r'name=["\']csrf_token["\']\s+value=["\']([0-9a-f]+)["\']', re.IGNORECASE
)


def _extract_csrf(html: str) -> str:
    m = _CSRF_RE.search(html) or _CSRF_INPUT_RE.search(html)
    if not m:
        raise RuntimeError("Could not extract CSRF token from Codeforces page")
    return m.group(1)


def _rand_ftaa() -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(random.choices(alphabet, k=18))


def _rand_bfaa() -> str:
    return secrets.token_hex(16)


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
        else:
            self._client = None
        self._http = httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
            },
        )

        self._contest_cache: dict[int, tuple[float, list[dict[str, Any]]]] = {}
        self._locks: dict[int, asyncio.Lock] = {}

        self._login_lock = asyncio.Lock()
        self._submit_lock = asyncio.Lock()
        self._logged_in = False
        self._ftaa = _rand_ftaa()
        self._bfaa = _rand_bfaa()

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
            external_url=f"https://codeforces.com/problemset/problem/{contest_id}/{index}",
        )

    # ---------- submit / poll ----------

    async def _login(self) -> None:
        if not self.account or not self.password:
            raise RuntimeError(
                "Codeforces service account is not configured: "
                "set CF_SERVICE_ACCOUNT and CF_SERVICE_PASSWORD"
            )
        async with self._login_lock:
            if self._logged_in:
                return

            r = await self._http.get(f"{CF_BASE}/enter")
            r.raise_for_status()
            csrf = _extract_csrf(r.text)

            r2 = await self._http.post(
                f"{CF_BASE}/enter",
                data={
                    "csrf_token": csrf,
                    "action": "enter",
                    "ftaa": self._ftaa,
                    "bfaa": self._bfaa,
                    "handleOrEmail": self.account,
                    "password": self.password,
                    "_tta": "176",
                    "remember": "on",
                },
            )
            r2.raise_for_status()
            # CF redirects to the profile page on success; the "logout" link
            # is present in the header markup of any authenticated page.
            if "/logout" not in r2.text:
                raise RuntimeError("Codeforces login failed (check credentials)")
            self._logged_in = True
            logger.info("Logged into Codeforces as %s", self.account)

    async def _latest_submission_id(self) -> int | None:
        """ID последней посылки сервисного аккаунта (через API)."""
        try:
            resp = await self._http.get(
                f"{CF_API}/user.status",
                params={"handle": self.account, "from": 1, "count": 1},
            )
            data = resp.json()
            if data.get("status") != "OK" or not data["result"]:
                return None
            return int(data["result"][0]["id"])
        except (httpx.HTTPError, ValueError, KeyError):
            return None

    async def submit(self, external_id: str, language: str, source_code: str) -> str:
        contest_id, index = _parse_external_id(external_id)
        program_type_id = CF_LANGUAGE_IDS.get(language.lower())
        if program_type_id is None:
            raise ValueError(
                f"Unsupported language {language!r}. Available: "
                f"{', '.join(sorted(CF_LANGUAGE_IDS))}"
            )

        # CF disallows duplicate source code submissions; добавим невидимый
        # маркер с timestamp, чтобы каждая посылка была уникальной.
        unique_marker = f"\n// algosyhub:{secrets.token_hex(8)}\n"
        source_to_send = source_code.rstrip() + unique_marker

        await self._login()

        # Serialize submits within one adapter instance — CF rate-limits and
        # we also want to deterministically match the resulting submission id.
        async with self._submit_lock:
            before_id = await self._latest_submission_id()

            r = await self._http.get(f"{CF_BASE}/problemset/submit")
            r.raise_for_status()
            csrf = _extract_csrf(r.text)

            resp = await self._http.post(
                f"{CF_BASE}/problemset/submit?csrf_token={csrf}",
                data={
                    "csrf_token": csrf,
                    "ftaa": self._ftaa,
                    "bfaa": self._bfaa,
                    "action": "submitSolutionFormSubmitted",
                    "submittedProblemCode": f"{contest_id}{index}",
                    "programTypeId": str(program_type_id),
                    "source": source_to_send,
                    "tabSize": "4",
                    "sourceCodeConfirmed": "true",
                    "_tta": "594",
                },
            )
            resp.raise_for_status()

            err = _extract_submit_error(resp.text)
            if err:
                raise RuntimeError(f"Codeforces rejected submission: {err}")

            # После успешного submit CF редиректит на /problemset/status.
            # Опрашиваем user.status, пока id не изменится — это наша посылка.
            for _ in range(20):
                latest = await self._latest_submission_id()
                if latest is not None and latest != before_id:
                    return str(latest)
                await asyncio.sleep(0.5)

            raise RuntimeError(
                "Codeforces accepted the form but the new submission did not "
                "appear in user.status within 10 seconds"
            )

    async def poll_verdict(self, external_submission_id: str) -> SubmissionResult:
        try:
            target_id = int(external_submission_id)
        except ValueError:
            raise ValueError(f"Invalid CF submission id: {external_submission_id!r}")

        # Грузим последние 50 посылок сервисного аккаунта — этого с большим
        # запасом хватит даже при активной отправке десятков студентов параллельно.
        resp = await self._http.get(
            f"{CF_API}/user.status",
            params={"handle": self.account, "from": 1, "count": 50},
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "OK":
            raise RuntimeError(f"CF API error: {data.get('comment')}")

        match = next((s for s in data["result"] if int(s["id"]) == target_id), None)
        if match is None:
            # Посылка уже выпала из последних 50 — считаем её ещё бегущей,
            # повторим попытку на следующей итерации поллера.
            return SubmissionResult(verdict=SubmissionVerdict.running)

        verdict_str = match.get("verdict")
        if verdict_str is None:
            return SubmissionResult(verdict=SubmissionVerdict.running)
        verdict = CF_VERDICT_MAP.get(verdict_str, SubmissionVerdict.rejected)

        time_ms = match.get("timeConsumedMillis")
        memory_bytes = match.get("memoryConsumedBytes")
        memory_mb = int(memory_bytes / (1024 * 1024)) if memory_bytes else None

        return SubmissionResult(verdict=verdict, time_ms=time_ms, memory_mb=memory_mb)


_ERROR_RE = re.compile(
    r'<span\s+class="error[^"]*">([^<]+)</span>', re.IGNORECASE
)


def _extract_submit_error(html: str) -> str | None:
    m = _ERROR_RE.search(html)
    if m:
        return m.group(1).strip()
    return None
