"""Timus archive (space=1): public statements and author submission history."""

import logging
import math
import re
from datetime import datetime, timezone
from html import escape
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup

from app.integrations.judges.base import ExternalSubmission, JudgeAdapter, ProblemData
from app.models.enums import SubmissionVerdict

if TYPE_CHECKING:
    from app.models.problem import Problem

logger = logging.getLogger(__name__)
TIMUS_BASE = "https://acm.timus.ru"
# Timus publishes local server times (UTC+5 today); ZoneInfo also handles
# historical submissions from before the Russian timezone changes.
TIMUS_TIMEZONE = ZoneInfo("Asia/Yekaterinburg")
MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        1,
    )
}
VERDICTS = {
    "accepted": SubmissionVerdict.accepted,
    "wrong answer": SubmissionVerdict.wrong_answer,
    "presentation error": SubmissionVerdict.wrong_answer,
    "time limit exceeded": SubmissionVerdict.time_limit,
    "idleness limit exceeded": SubmissionVerdict.time_limit,
    "memory limit exceeded": SubmissionVerdict.memory_limit,
    "runtime error": SubmissionVerdict.runtime_error,
    "compilation error": SubmissionVerdict.compilation_error,
    "output limit exceeded": SubmissionVerdict.rejected,
    "restricted function": SubmissionVerdict.rejected,
    "in queue": SubmissionVerdict.pending,
    "waiting": SubmissionVerdict.pending,
    "compiling": SubmissionVerdict.running,
    "running": SubmissionVerdict.running,
    "testing": SubmissionVerdict.running,
}


def parse_problem_id(value: str) -> str:
    value = value.strip()
    if not value.isascii() or not value.isdigit():
        parsed = urlparse(value.lower())
        query = parse_qs(parsed.query)
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname not in {"acm.timus.ru", "timus.online"}
            or parsed.path != "/problem.aspx"
            or query.get("space", ["1"]) != ["1"]
        ):
            raise ValueError("Укажите номер задачи Timus, например 1000")
        value = query.get("num", [""])[0]
    if not re.fullmatch(r"[0-9]{4}", value) or int(value) < 1000:
        raise ValueError("Укажите номер задачи Timus, например 1000")
    return value


def parse_author_id(value: str) -> str:
    value = value.strip()
    if not re.fullmatch(r"[0-9]+", value) or int(value) == 0:
        raise ValueError(
            "Timus: нужен числовой id из ссылки author.aspx?id=…, не JUDGE_ID"
        )
    return str(int(value))


def _parse_date(value: str) -> datetime:
    # English status pages: "21:48:17 24 Sep 2026". Avoid strptime's
    # locale-dependent month names and never substitute now for a bad date.
    time, day, month, year = value.split()
    hour, minute, second = map(int, time.split(":"))
    return datetime(
        int(year), MONTHS[month], int(day), hour, minute, second, tzinfo=TIMUS_TIMEZONE
    ).astimezone(timezone.utc)


def _memory_mb(value: str) -> int | None:
    match = re.fullmatch(r"([\d.]+)\s*(KB|MB)", value, re.IGNORECASE)
    if not match:
        return None
    size = float(match[1])
    return math.ceil(size / 1024 if match[2].upper() == "KB" else size)


class TimusAdapter(JudgeAdapter):
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 AlgosyHub/0.1"},
        )

    async def _get(self, path: str, **params: str | int) -> BeautifulSoup:
        try:
            response = await self._http.get(f"{TIMUS_BASE}/{path}", params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Timus request failed: {exc}") from exc
        return BeautifulSoup(response.text, "html.parser")

    async def _problem_page(self, external_id: str) -> BeautifulSoup:
        number = parse_problem_id(external_id)
        soup = await self._get("problem.aspx", space=1, num=number, locale="ru")
        title = soup.select_one(".problem_title")
        if title is None or not title.get_text(strip=True).startswith(f"{number}."):
            raise ValueError(f"Задача {number} не найдена на Timus")
        return soup

    async def fetch_problem(self, external_id: str) -> ProblemData:
        number = parse_problem_id(external_id)
        soup = await self._problem_page(number)
        title = soup.select_one(".problem_title").get_text(" ", strip=True)
        tags = [a.get_text(" ", strip=True) for a in soup.select('a[href*="tag="]')]
        links = soup.select_one(".problem_links")
        difficulty = re.search(
            r"(?:Сложность|Difficulty):\s*(\d+)",
            links.get_text(" ", strip=True) if links else "",
        )
        return ProblemData(
            external_id=number,
            title=title.split(".", 1)[1].strip(),
            external_url=f"{TIMUS_BASE}/problem.aspx?space=1&num={number}",
            tags=list(dict.fromkeys(tags)),
            difficulty=int(difficulty[1]) if difficulty else None,
        )

    async def render_statement_html(self, problem: "Problem") -> str:
        soup = await self._problem_page(problem.external_id)
        block = soup.select_one(".problem_content")
        if block is None:
            raise RuntimeError("Timus statement markup has changed")
        return (
            '<!doctype html><html lang="ru"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<base href="{TIMUS_BASE}/"><title>{escape(problem.title)}</title>'
            '<link rel="stylesheet" href="/style58.css">'
            "<style>body{margin:20px}.problem_content{max-width:880px;margin:auto}"
            "img{max-width:100%}pre{overflow:auto}</style></head>"
            f"<body>{block}</body></html>"
        )

    async def fetch_statement_text(self, problem: "Problem") -> str | None:
        soup = await self._problem_page(problem.external_id)
        block = soup.select_one(".problem_content")
        return block.get_text("\n", strip=True) if block else None

    def submit_url(self, contest_external_id: str, problem_index: str) -> str:
        number = parse_problem_id(problem_index)
        return f"{TIMUS_BASE}/submit.aspx?space=1&num={number}"

    async def fetch_user_submissions(
        self, handle: str, count: int = 50
    ) -> list[ExternalSubmission]:
        author = parse_author_id(handle)
        if count <= 0:
            return []
        # Timus offers page sizes 10, 30 and 100.
        count = min(count, 100)
        page_size = next(size for size in (10, 30, 100) if size >= count)
        soup = await self._get(
            "status.aspx", space=1, author=author, count=page_size, locale="en"
        )
        table = soup.select_one("table.status")
        if table is None:
            raise RuntimeError("Timus submission table not found")
        submissions = []
        for row in table.select("tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) != 9 or "id" not in cells[0].get("class", []):
                continue
            try:
                author_link = cells[2].find("a", href=True)
                problem_link = cells[3].find("a", href=True)
                if author_link is None or problem_link is None:
                    continue
                if parse_qs(urlparse(author_link["href"]).query).get("id") != [author]:
                    continue
                number = parse_problem_id(
                    f"{TIMUS_BASE}/{problem_link['href'].lstrip('/')}"
                )
                submitted_at = _parse_date(cells[1].get_text(" ", strip=True))
                run_id = cells[0].get_text(strip=True)
                if not run_id.isdigit():
                    continue
                verdict_text = cells[5].get_text(" ", strip=True).lower()
                verdict = next(
                    (
                        value
                        for key, value in VERDICTS.items()
                        if verdict_text.startswith(key)
                    ),
                    SubmissionVerdict.rejected,
                )
                runtime = cells[7].get_text(strip=True)
                submissions.append(
                    ExternalSubmission(
                        external_id=run_id,
                        external_problem_id=number,
                        language=cells[4].get_text(" ", strip=True),
                        verdict=verdict,
                        submitted_at=submitted_at,
                        time_ms=round(float(runtime) * 1000) if runtime else None,
                        memory_mb=_memory_mb(cells[8].get_text(" ", strip=True)),
                        submission_url=f"{TIMUS_BASE}/status.aspx?space=1&author={author}",
                    )
                )
            except (ValueError, KeyError):
                logger.warning("Skipping malformed Timus submission row")
            if len(submissions) >= count:
                break
        return submissions
