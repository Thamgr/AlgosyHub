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
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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


# Codeforces размещает CSRF-токен в нескольких местах на странице. Ищем по
# любому из них, чтобы быть устойчивыми к косметическим правкам шаблона:
#   <meta name="X-Csrf-Token" content="..."/>            ← в <head>
#   <span class="csrf-token" data-csrf="..."></span>     ← рядом с формой
#   <input type="hidden" name="csrf_token" value="..."/> ← в самих формах
_DATA_CSRF_RE = re.compile(r'data-csrf=["\']([0-9a-f]{16,})["\']', re.IGNORECASE)
_META_CSRF_RE = re.compile(
    r'<meta\s[^>]*name=["\']X-Csrf-Token["\'][^>]*content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_META_CSRF_REV_RE = re.compile(
    r'<meta\s[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']X-Csrf-Token["\']',
    re.IGNORECASE,
)
_INPUT_CSRF_RE = re.compile(
    r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', re.IGNORECASE
)


def _extract_csrf(html: str) -> str:
    for rx in (_DATA_CSRF_RE, _META_CSRF_RE, _META_CSRF_REV_RE, _INPUT_CSRF_RE):
        m = rx.search(html)
        if m:
            return m.group(1)
    snippet = html[:500].replace("\n", " ")
    logger.warning(
        "Could not extract CSRF token. First 500 chars of CF response: %s", snippet
    )
    raise RuntimeError("Could not extract CSRF token from Codeforces page")


# Codeforces периодически защищает страницы JS-челленджем (RCPC): сначала
# приходит маленький HTML c вызовами `toNumbers("…")` и `slowAES.decrypt(...)`,
# который в браузере вычисляет cookie `RCPC` и перезагружает страницу.
# Эмулируем эту проверку: AES-128-CBC расшифровка трёх hex-аргументов даёт
# значение cookie, которое нужно поставить и повторить запрос.
_RCPC_RE = re.compile(
    r'toNumbers\("([0-9a-f]+)"\).*?'
    r'toNumbers\("([0-9a-f]+)"\).*?'
    r'toNumbers\("([0-9a-f]+)"\)',
    re.DOTALL,
)


def _solve_rcpc(html: str) -> str | None:
    if "slowAES" not in html and "toNumbers(" not in html:
        return None
    m = _RCPC_RE.search(html)
    if not m:
        logger.warning(
            "Codeforces returned an RCPC-like page that does not match the "
            "expected toNumbers(...) pattern; cannot bypass automatically"
        )
        return None
    key = bytes.fromhex(m.group(1))
    iv = bytes.fromhex(m.group(2))
    ct = bytes.fromhex(m.group(3))
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    pt = decryptor.update(ct) + decryptor.finalize()
    return pt.hex()


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
        session_cookie: str = "",
    ) -> None:
        self.account = account
        self.password = password
        self._api_key = api_key
        self._api_secret = api_secret
        self._session_cookie = session_cookie.strip()

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

        if self._session_cookie:
            self._inject_cookie_header(self._session_cookie)

    def _inject_cookie_header(self, raw: str) -> None:
        """Парсит строку из браузерного заголовка `Cookie:` (name=value; …)
        и складывает все пары в http-клиент."""
        count = 0
        for part in raw.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            name, _, value = part.partition("=")
            name, value = name.strip(), value.strip()
            if not name:
                continue
            self._http.cookies.set(
                name, value, domain="codeforces.com", path="/"
            )
            count += 1
        logger.info("Injected %d Codeforces session cookies from env", count)

    def _lock_for(self, contest_id: int) -> asyncio.Lock:
        lock = self._locks.get(contest_id)
        if lock is None:
            lock = asyncio.Lock()
            self._locks[contest_id] = lock
        return lock

    async def _ensure_rcpc(self, response: httpx.Response) -> bool:
        """Если CF прислал RCPC-челлендж, ставит cookie и возвращает True."""
        rcpc = _solve_rcpc(response.text)
        if not rcpc:
            return False
        self._http.cookies.set("RCPC", rcpc, domain="codeforces.com", path="/")
        logger.info("Solved Codeforces RCPC challenge")
        return True

    async def _web_get(self, url: str, **kwargs: Any) -> httpx.Response:
        r = await self._http.get(url, **kwargs)
        if await self._ensure_rcpc(r):
            r = await self._http.get(url, **kwargs)
        return r

    async def _web_post(self, url: str, **kwargs: Any) -> httpx.Response:
        r = await self._http.post(url, **kwargs)
        if await self._ensure_rcpc(r):
            r = await self._http.post(url, **kwargs)
        return r

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

    async def _check_logged_in(self) -> bool:
        """Проверяет, авторизованы ли мы прямо сейчас (по присутствию /logout)."""
        try:
            r = await self._web_get(f"{CF_BASE}/")
            return r.status_code == 200 and "/logout" in r.text
        except httpx.HTTPError:
            return False

    async def _login(self) -> None:
        if not self.account:
            raise RuntimeError(
                "Codeforces service account is not configured: set CF_SERVICE_ACCOUNT"
            )
        async with self._login_lock:
            if self._logged_in:
                return

            # Режим 1 — куки из браузера. Программный логин CF блокирует
            # Cloudflare-ом, поэтому это самый надёжный путь.
            if self._session_cookie:
                if await self._check_logged_in():
                    self._logged_in = True
                    logger.info(
                        "Codeforces session cookie is valid (logged in as %s)",
                        self.account,
                    )
                    return
                raise RuntimeError(
                    "Provided CF_SESSION_COOKIE is invalid or expired — "
                    "log into Codeforces in a browser and copy a fresh "
                    "`Cookie:` header"
                )

            # Режим 2 — программный логин логин+пароль (часто блокируется CF).
            if not self.password:
                raise RuntimeError(
                    "Codeforces auth is not configured: set CF_SESSION_COOKIE "
                    "(recommended) or CF_SERVICE_PASSWORD"
                )

            r = await self._web_get(f"{CF_BASE}/enter")
            r.raise_for_status()
            csrf = _extract_csrf(r.text)

            r2 = await self._web_post(
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
            if "/logout" not in r2.text:
                raise RuntimeError(
                    "Codeforces login failed (Cloudflare may block "
                    "programmatic logins — try CF_SESSION_COOKIE)"
                )
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

            submit_page = f"{CF_BASE}/contest/{contest_id}/submit"
            r = await self._web_get(submit_page)
            r.raise_for_status()
            csrf = _extract_csrf(r.text)

            # Формат заимствован из рабочего https://github.com/Nirlep5252/codeforces-cli/blob/main/cf/submit.py
            # — contest-specific URL + submittedProblemIndex (lowercase!) + contestId.
            # CF тихо отбрасывает форму, если index в верхнем регистре, потому что
            # <option value="..."> в дропдауне всегда lowercase ("a", "b", "f2", …).
            resp = await self._web_post(
                f"{submit_page}?csrf_token={csrf}",
                data={
                    "csrf_token": csrf,
                    "ftaa": "",
                    "bfaa": "",
                    "action": "submitSolutionFormSubmitted",
                    "submittedProblemIndex": index.lower(),
                    "programTypeId": str(program_type_id),
                    "contestId": str(contest_id),
                    "source": source_to_send,
                    "tabSize": "4",
                    "sourceCodeConfirmed": "true",
                },
            )
            resp.raise_for_status()

            err = _extract_submit_error(resp.text)
            if err:
                raise RuntimeError(f"Codeforces rejected submission: {err}")

            # CF после успешного submit редиректит на /contest/{id}/my.
            # Если этого не случилось — форма была отвергнута без видимой ошибки
            # (rate-limit, дублёр кода, неверный язык, etc.). Не ждём 10 секунд
            # впустую, сразу логируем подсказку и фейлим.
            final_url = str(resp.url)
            success_prefix = f"{CF_BASE}/contest/{contest_id}/my"
            if not final_url.startswith(success_prefix):
                hint = _diagnose_submit_failure(resp.text)
                logger.warning(
                    "Submit form was not redirected to %s.\n"
                    "  final URL: %s\n  hint: %s\n  HTML head: %s",
                    success_prefix,
                    final_url,
                    hint or "(no recognised phrase)",
                    resp.text[:500].replace("\n", " "),
                )
                raise RuntimeError(
                    f"Codeforces did not accept submission (no redirect to /my). "
                    f"Final URL: {final_url}. "
                    f"{('Reason: ' + hint) if hint else 'Check backend logs for HTML dump.'}"
                )

            logger.info("Submit posted; final URL=%s; latest_before=%s", final_url, before_id)

            for _ in range(20):
                latest = await self._latest_submission_id()
                if latest is not None and latest != before_id:
                    return str(latest)
                await asyncio.sleep(0.5)

            raise RuntimeError(
                "Codeforces redirected to /my but the new submission did not "
                "appear in user.status within 10 seconds (this should not happen)"
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


# Список фраз, которые CF выводит на странице submit-формы при «тихом» отказе
# (без <span class="error">). Берём кусок html вокруг найденной фразы — этого
# хватает, чтобы понять причину при отладке.
_FAILURE_HINTS = (
    "you have submitted exactly the same code before",
    "you can submit at most",
    "you can submit no more than",
    "you are not allowed to submit",
    "you have not chosen a programming language",
    "choose a problem",
    "choose a valid",
    "wrong submission",
    "try again",
    "please wait",
)


def _diagnose_submit_failure(html: str) -> str | None:
    lc = html.lower()
    for phrase in _FAILURE_HINTS:
        idx = lc.find(phrase)
        if idx != -1:
            return html[max(0, idx - 30): idx + 200].strip()
    return None
