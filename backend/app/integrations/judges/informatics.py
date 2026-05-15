import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import httpx

from app.core.config import settings
from app.integrations.judges.base import ExternalSubmission, JudgeAdapter, ProblemData
from app.models.enums import SubmissionVerdict

if TYPE_CHECKING:
    from app.models.problem import Problem

logger = logging.getLogger(__name__)

INF_BASE = "https://informatics.msk.ru"


_INF_STATEMENT_TEMPLATE = """<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<base href="{base}/">
<title>{title}</title>
<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['\\\\(', '\\\\)']],
    displayMath: [['\\\\[', '\\\\]']]
  }},
  svg: {{ fontCache: 'global' }}
}};
</script>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js" async></script>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
      Helvetica, Arial, sans-serif;
    color: #1f2328;
    line-height: 1.55;
    margin: 0;
    padding: 20px;
    background: #fff;
  }}
  .title {{
    font-size: 1.5em;
    font-weight: 600;
    margin: 0 0 10px;
    text-align: center;
  }}
  .limits {{
    text-align: center;
    color: #57606a;
    font-size: 0.9em;
    margin-bottom: 20px;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 14px;
  }}
  .problem-statement {{ max-width: 880px; margin: 0 auto; }}
  .problem-statement p {{ margin: 8px 0; }}
  .problem-statement .legend {{ margin-bottom: 14px; }}
  .problem-statement .section-title {{
    font-size: 1.1em;
    font-weight: 600;
    margin: 22px 0 8px;
  }}
  .problem-statement pre {{
    background: #f6f8fa;
    padding: 10px 14px;
    border-radius: 6px;
    overflow-x: auto;
    font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo,
      Consolas, monospace;
    font-size: 0.92em;
    line-height: 1.45;
    white-space: pre;
    margin: 0;
  }}
  .problem-statement table {{ border-collapse: collapse; margin: 8px 0; }}
  .problem-statement table th,
  .problem-statement table td {{
    border: 1px solid #d0d7de;
    padding: 4px 8px;
  }}
  .problem-statement img {{ max-width: 100%; }}
  .problem-statement ul,
  .problem-statement ol {{ padding-left: 1.4em; }}
  .sample-tests .sample-test {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 14px;
    margin: 8px 0;
  }}
  .sample-tests .sample-test .title {{
    font-weight: 600;
    padding: 4px 0;
  }}
  @media (max-width: 640px) {{
    .sample-tests .sample-test {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


# Маппинг кодов вердиктов ejudge → наш `SubmissionVerdict`. Источник —
# `submits/js/module.js` (`statuses_map` + список селектов): 0=OK, 1=CE, 2=RE,
# 3=TL, 4=PE, 5=WA, 6=CF (check failed), 7=Partial, 8=AC (зачтено вручную),
# 9=Ignore, 10=Disqualified, 11=Pending, 12=ML, 13=Security, 14=Style,
# 96=Running (rejudge), 98=Compiling, 377=In queue, 520=Submit error.
INF_STATUS_MAP: dict[int, SubmissionVerdict] = {
    0: SubmissionVerdict.accepted,
    1: SubmissionVerdict.compilation_error,
    2: SubmissionVerdict.runtime_error,
    3: SubmissionVerdict.time_limit,
    4: SubmissionVerdict.wrong_answer,
    5: SubmissionVerdict.wrong_answer,
    6: SubmissionVerdict.rejected,
    7: SubmissionVerdict.wrong_answer,  # частичное решение — не AC
    8: SubmissionVerdict.accepted,
    9: SubmissionVerdict.rejected,
    10: SubmissionVerdict.rejected,
    11: SubmissionVerdict.pending,
    12: SubmissionVerdict.memory_limit,
    13: SubmissionVerdict.rejected,
    14: SubmissionVerdict.rejected,
    96: SubmissionVerdict.running,
    98: SubmissionVerdict.running,
    377: SubmissionVerdict.pending,
    520: SubmissionVerdict.rejected,
}

# Маппинг id языка ejudge → человекочитаемое имя. Источник — `submits/js/map.js`.
# Незнакомые id показываем как "lang-<id>".
INF_LANG_MAP: dict[int, str] = {
    1: "Free Pascal",
    2: "GNU C",
    3: "GNU C++",
    7: "Turbo Pascal",
    8: "Borland Delphi",
    9: "Borland C",
    10: "Borland C++",
    18: "Java",
    22: "PHP",
    23: "Python 2",
    24: "Perl",
    25: "Mono C#",
    26: "Ruby",
    27: "Python 3",
    28: "Haskell",
    29: "FreeBASIC",
    30: "PascalABC",
    53: "Go",
    68: "GNU C++ (sanitizer)",
    71: "Kotlin",
    89: "Scala",
}


class InformaticsAdapter(JudgeAdapter):
    """Адаптер informatics.msk.ru.

    Информатикс — это Moodle с самописным плагином `mod_statements` и ejudge'ом
    под капотом. Задача идентифицируется числовым ``chapterid`` (он же
    ``problem.id`` в JSON-ответах ejudge — это совпадает).

    Условия задач отдаются публично, а вот посылки — только из-под Moodle-сессии.
    Поэтому здесь живёт мини-клиент, который логинится одним сервисным
    аккаунтом-наблюдателем (см. ``settings.INFORMATICS_USERNAME/PASSWORD``)
    и переиспользует cookie ``MoodleSession``. Если креды не заданы — адаптер
    остаётся в read-only режиме: задачи импортировать можно, посылки — нет.
    """

    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0 AlgosyHub/0.1"},
            follow_redirects=True,
        )
        self._session_lock = asyncio.Lock()
        self._logged_in = False

    @staticmethod
    def _normalize_external_id(external_id: str) -> str:
        s = external_id.strip()
        # Иногда удобно вставить URL целиком — вытащим chapterid (фронт
        # дополнительно делает `.toUpperCase()`, поэтому матчим без регистра).
        m = re.search(r"chapterid=(\d+)", s, re.IGNORECASE)
        if m:
            return m.group(1)
        if not s.isdigit():
            raise ValueError(
                f"Invalid Informatics problem id: {external_id!r}. "
                "Expected a positive integer (chapterid) or full statement URL."
            )
        return s

    @staticmethod
    def problem_url(chapter_id: str) -> str:
        return f"{INF_BASE}/mod/statements/view.php?chapterid={chapter_id}"

    # -- problem import -------------------------------------------------------

    async def fetch_problem(self, external_id: str) -> ProblemData:
        chapter_id = self._normalize_external_id(external_id)
        url = self.problem_url(chapter_id)

        try:
            resp = await self._http.get(url)
        except httpx.HTTPError as e:
            raise RuntimeError(f"Informatics request failed: {e}") from e

        if resp.status_code == 404:
            raise ValueError(
                f"Problem chapterid={chapter_id} not found on Informatics"
            )
        if resp.status_code != 200:
            raise RuntimeError(
                f"Informatics HTTP {resp.status_code} for chapterid={chapter_id}"
            )

        title = self._extract_title(resp.text, chapter_id)
        return ProblemData(
            external_id=chapter_id,
            title=title,
            tags=[],
            difficulty=None,
            external_url=url,
        )

    @staticmethod
    def _extract_title(html: str, chapter_id: str) -> str:
        """Вытащить «человеческое» название из страницы условия.

        Информатикс отдаёт заголовок и в ``<title>``, и в ``<h2>``
        в формате ``Задача №N. Имя``. Нам нужно только ``Имя``.
        """
        raw: str | None = None
        try:
            from bs4 import BeautifulSoup  # type: ignore[import-not-found]

            soup = BeautifulSoup(html, "html.parser")
            h2 = soup.find("h2")
            if h2 and h2.get_text(strip=True):
                raw = h2.get_text(strip=True)
            else:
                t = soup.find("title")
                if t:
                    raw = t.get_text(strip=True)
        except ImportError:
            m = re.search(
                r"<h2[^>]*>([^<]+)</h2>|<title>([^<]+)</title>",
                html,
                re.IGNORECASE,
            )
            if m:
                raw = (m.group(1) or m.group(2) or "").strip()

        if not raw:
            return f"Информатикс №{chapter_id}"

        # «Задача №10. Имя» → «Имя». Учитываем и узкий, и обычный пробелы.
        m = re.match(
            rf"^Задача\s*№\s*{re.escape(chapter_id)}\.\s*(.+)$",
            raw,
        )
        if m:
            return m.group(1).strip()
        return raw

    async def render_statement_html(self, problem: "Problem") -> str:
        """Возвращает чистую страницу только с условием задачи.

        Дефолт `JudgeAdapter.render_statement_html` отдаёт всю страницу
        Информатикса целиком — а это полная тема Moodle с навигацией,
        сайдбаром, футером и кучей JS, ради которого условие тонет где-то
        в середине iframe. Здесь делаем то же, что и для CF: вырезаем
        ровно блоки с условием (`div.problem-statement`) + заголовок и
        блок «Ограничения», и оборачиваем в минимальный шаблон с
        MathJax-делимитерами `\\(...\\)` и `\\[...\\]`, как у самого
        Информатикса.
        """
        try:
            resp = await self._http.get(problem.external_url)
        except httpx.HTTPError as e:
            raise RuntimeError(f"Informatics statement fetch failed: {e}") from e
        if resp.status_code != 200:
            raise RuntimeError(
                f"Informatics statement HTTP {resp.status_code} for "
                f"{problem.external_url}"
            )

        try:
            from bs4 import BeautifulSoup  # type: ignore[import-not-found]
        except ImportError:
            # Без bs4 не вырежем кусок — отдадим дефолтную полную страницу.
            return await super().render_statement_html(problem)

        soup = BeautifulSoup(resp.text, "html.parser")

        body_parts: list[str] = []
        h2 = soup.find("h2")
        if h2 and h2.get_text(strip=True):
            body_parts.append(f"<h1 class='title'>{h2.decode_contents()}</h1>")

        # Лимиты времени/памяти — на оригинальной странице в сайдбаре,
        # здесь подаём отдельной строкой над условием.
        for sec in soup.select("section.block_statements_menu"):
            title_el = sec.find(class_="card-title")
            body_el = sec.find(class_="card-text")
            if not title_el or not body_el:
                continue
            if "Ограничения" in title_el.get_text(strip=True):
                limits = _inline_text(body_el)
                if limits:
                    body_parts.append(
                        f"<div class='limits'><b>Ограничения:</b> {limits}</div>"
                    )
                break

        blocks = soup.select("div.problem-statement")
        if not blocks:
            # Не нашли — лучше отдать полную страницу с <base href>,
            # чем пустоту.
            return await super().render_statement_html(problem)
        for block in blocks:
            body_parts.append(str(block))

        return _INF_STATEMENT_TEMPLATE.format(
            base=INF_BASE,
            title=f"{problem.external_id} — {problem.title}",
            body="\n".join(body_parts),
        )

    async def fetch_statement_text(self, problem: "Problem") -> str | None:
        """Plain-text условие задачи для подсказчика-LLM.

        Информатикс верстает условие в двух соседних ``div.problem-statement``:
        первый — текст с input/output-specifications, второй — sample-tests.
        Берём оба, плюс заголовок и блок «Ограничения» из сайдбара. Внутри
        бежим вручную, а не одним ``get_text("\\n")``, чтобы инлайн-теги
        вроде ``<span><i>N</i></span>`` (математические переменные) не
        разваливали каждое предложение на десяток строк.
        """
        try:
            resp = await self._http.get(problem.external_url)
        except httpx.HTTPError as e:
            logger.warning("Informatics statement fetch failed: %s", e)
            return None
        if resp.status_code != 200:
            logger.warning(
                "Informatics statement HTTP %s for %s",
                resp.status_code,
                problem.external_url,
            )
            return None

        try:
            from bs4 import BeautifulSoup  # type: ignore[import-not-found]
        except ImportError:
            logger.warning(
                "beautifulsoup4 not installed, can't extract Informatics statement"
            )
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        parts: list[str] = []

        h2 = soup.find("h2")
        if h2 and h2.get_text(strip=True):
            parts.append(_inline_text(h2))

        # Сайдбар «Ограничения» — лимиты времени/памяти. Без авторизации
        # рендерится таким же блоком, что и в админ-режиме, но с одной
        # строкой `2 сек. 64 MiB`.
        for sec in soup.select("section.block_statements_menu"):
            title_el = sec.find(class_="card-title")
            body_el = sec.find(class_="card-text")
            if not title_el or not body_el:
                continue
            if "Ограничения" in title_el.get_text(strip=True):
                limits = _inline_text(body_el)
                if limits:
                    parts.append(f"Ограничения: {limits}")
                break

        for block in soup.select("div.problem-statement"):
            chunk: list[str] = []
            _walk_block(block, chunk)
            if chunk:
                parts.append("\n\n".join(chunk))

        text = "\n\n".join(parts)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text or None

    # -- session management ---------------------------------------------------

    async def _login(self) -> bool:
        """Авторизуемся в Moodle. Возвращает ``True``, если в http-клиенте
        теперь живая сессия (cookie ``MoodleSession``).

        Идея проста: Moodle защищает форму логина CSRF-токеном
        ``logintoken`` — нужно сначала GET-нуть страницу логина, выдрать
        его из HTML и затем POST-нуть учётку.
        """
        username = settings.INFORMATICS_USERNAME
        password = settings.INFORMATICS_PASSWORD
        if not username or not password:
            return False

        try:
            resp = await self._http.get(f"{INF_BASE}/login/index.php")
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Informatics login GET failed: %s", e)
            return False

        m = re.search(r'name="logintoken" value="([^"]+)"', resp.text)
        if not m:
            logger.warning(
                "Informatics login: logintoken not found on /login/index.php"
            )
            return False
        token = m.group(1)

        try:
            resp = await self._http.post(
                f"{INF_BASE}/login/index.php",
                data={
                    "username": username,
                    "password": password,
                    "logintoken": token,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.warning("Informatics login POST failed: %s", e)
            return False

        # Moodle на удачный логин редиректит на `/`. На неудачный — обратно
        # на `/login/index.php` с уведомлением `loginerrors`. Грубой проверки
        # по тексту достаточно: явная подпись или текст ошибки.
        body_lower = resp.text.lower()
        if "loginerrors" in body_lower or "/login/index.php" in str(resp.url):
            logger.warning("Informatics login failed (bad credentials?)")
            return False

        logger.info("Informatics: logged in as %s", username)
        return True

    async def _ensure_logged_in(self) -> bool:
        if self._logged_in:
            return True
        async with self._session_lock:
            if self._logged_in:
                return True
            ok = await self._login()
            self._logged_in = ok
            return ok

    async def _force_relogin(self) -> bool:
        """Сбросить cookie и залогиниться заново.

        Так делаем, когда удалённый ответ говорит "Not authorized" — значит,
        либо сессия истекла (TTL у Moodle 4 часа), либо нас выкинули.
        """
        async with self._session_lock:
            self._http.cookies.clear()
            self._logged_in = False
            ok = await self._login()
            self._logged_in = ok
            return ok

    # -- submissions polling --------------------------------------------------

    async def _filter_runs(
        self, user_id: str, count: int, page: int = 1
    ) -> dict[str, Any]:
        params = {
            # Параметры скопированы из формы submits/view.php — лишних не
            # шлём. ``problem_id=0`` и ``status_id=-1`` означают «все задачи,
            # любой статус», ``count`` — размер страницы, ``page`` — с 1.
            "problem_id": 0,
            "from_timestamp": -1,
            "to_timestamp": -1,
            "user_id": user_id,
            "lang_id": -1,
            "status_id": -1,
            "statement_id": "",
            "count": count,
            "with_comment": "",
            "page": page,
            "group_id": 0,
        }
        resp = await self._http.get(
            f"{INF_BASE}/py/problem/0/filter-runs", params=params
        )
        resp.raise_for_status()
        return resp.json()

    async def fetch_user_submissions(
        self, handle: str, count: int = 50
    ) -> list[ExternalSubmission]:
        # На Информатиксе пользователь идентифицируется числовым ``user_id``
        # (видно в URL `/submits/view.php?user_id=355608`). Никакого ника
        # для API нет — поэтому если ученик ввёл строку, не являющуюся
        # числом, просто пропускаем.
        handle = handle.strip()
        if not handle.isdigit():
            logger.warning(
                "Informatics handle must be a numeric user_id, got: %r", handle
            )
            return []

        if not await self._ensure_logged_in():
            # Креды не заданы или логин не прошёл — молча скипаем,
            # подробный warning уже залогирован в `_login`.
            return []

        try:
            data = await self._filter_runs(handle, count=count, page=1)
        except httpx.HTTPError as e:
            logger.warning("Informatics filter-runs HTTP error: %s", e)
            return []

        # «Сессия протухла» — повторяем один раз после re-login.
        if data.get("result") != "success":
            logger.info(
                "Informatics filter-runs returned %r, re-authenticating",
                data.get("message"),
            )
            if not await self._force_relogin():
                return []
            try:
                data = await self._filter_runs(handle, count=count, page=1)
            except httpx.HTTPError as e:
                logger.warning("Informatics filter-runs HTTP error after relogin: %s", e)
                return []
            if data.get("result") != "success":
                logger.warning(
                    "Informatics filter-runs still failing after relogin: %r",
                    data.get("message"),
                )
                return []

        out: list[ExternalSubmission] = []
        for row in data.get("data") or []:
            problem = row.get("problem") or {}
            problem_id = problem.get("id")
            run_id = row.get("id")
            if problem_id is None or run_id is None:
                continue

            submitted_at = _parse_create_time(row.get("create_time"))
            verdict = INF_STATUS_MAP.get(
                row.get("ejudge_status"), SubmissionVerdict.rejected
            )
            lang_id = row.get("ejudge_language_id")
            language = INF_LANG_MAP.get(
                lang_id,
                f"informatics-lang-{lang_id}" if lang_id is not None else "unknown",
            )

            out.append(
                ExternalSubmission(
                    external_id=str(run_id),
                    external_problem_id=str(problem_id),
                    language=language,
                    verdict=verdict,
                    submitted_at=submitted_at,
                    # Информатикс не публикует индивидуальные URL посылок
                    # для не-админов — даём ссылку на список юзера.
                    submission_url=(
                        f"{INF_BASE}/submits/view.php?user_id={handle}"
                    ),
                    # Время/память на этом эндпойнте не возвращаются —
                    # для них есть отдельный /py/protocol/get_submit/...,
                    # но он тоже только для админов.
                )
            )
        return out


def _parse_create_time(value: Any) -> datetime:
    """ISO8601 со смещением → aware-datetime в UTC.

    Если поля нет / оно битое — возвращаем «сейчас», чтобы посылка не
    проваливалась в эпоху и сортировки не ломались.
    """
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(tz=timezone.utc)


# -- statement-text helpers ----------------------------------------------------
# Импорт BeautifulSoup ленивый (внутри `fetch_statement_text`), поэтому
# здесь типы аннотируем как `Any` — без жёсткой зависимости в runtime.


def _inline_text(node: Any) -> str:
    """Текст элемента в одну строку, схлопнутые пробелы.

    Используется для абзацев и заголовков: в исходнике они часто
    утыканы инлайн-тегами (``<span lang="en-US"><i>N</i></span>``,
    ``<sup>``, ``<font>``), и обычный ``get_text("\\n")`` рвал бы
    каждое предложение на десяток строк.
    """
    text = node.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def _walk_block(node: Any, out: list[str]) -> None:
    """Рендерим блочный узел в массив абзацев.

    Идея: бежим по детям; ``<p>``, ``<li>`` склеиваем в одну строку,
    ``<pre>`` сохраняем с переносами (это сэмпл-тесты), вложенные
    ``<div>`` рекурсивно разбираем — кроме «титулов» секций
    (``section-title``/``title`` в `sample-test`), которые отдаются
    отдельным абзацем-заголовком.
    """
    from bs4 import NavigableString, Tag  # type: ignore[import-not-found]

    for child in node.children:
        if isinstance(child, NavigableString):
            text = re.sub(r"\s+", " ", str(child)).strip()
            if text:
                out.append(text)
            continue
        if not isinstance(child, Tag):
            continue
        if child.name == "pre":
            text = child.get_text().strip()
            if text:
                out.append(text)
        elif child.name in {"p", "li"}:
            text = _inline_text(child)
            if text:
                out.append(text)
        elif child.name == "div":
            classes = child.get("class") or []
            if "section-title" in classes or "title" in classes:
                title = _inline_text(child)
                if title:
                    out.append(title)
            else:
                _walk_block(child, out)
        # Прочие inline-теги игнорируем — они уже подцепились внутри <p>.
