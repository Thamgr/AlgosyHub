from datetime import datetime, timezone
from types import SimpleNamespace

import httpx
import pytest
import pytest_asyncio
from app.integrations.judges.timus import (
    TimusAdapter,
    parse_author_id,
    parse_problem_id,
)
from app.models.enums import SubmissionVerdict

# Reduced fixtures use the structure of Timus' public problem/status pages.
PROBLEM_HTML = """<div class="problem_content"><h2 class="problem_title">1000. A+B Problem</h2>
<div id="problem_text">Calculate a+b<table class="sample"><tr><td><pre>1 5</pre></td>
<td><pre>6</pre></td></tr></table></div></div>
<a href="problemset.aspx?space=1&amp;tag=beginners">beginners</a>
<div class="problem_links"><span>Сложность: 16</span></div>"""


def status_row(
    run_id="123", verdict="Accepted", date="21:48:17 24 Sep 2026", author="42"
):
    return f"""<tr class="even"><td class="id">{run_id}</td><td class="date">{date}</td>
    <td class="coder"><a href="author.aspx?id={author}">Student</a></td>
    <td class="problem"><a href="problem.aspx?space=1&amp;num=1000">1000</a></td>
    <td class="language">G++ 13.2 x64</td><td class="verdict_ac">{verdict}</td>
    <td class="test"></td><td class="runtime">0.062</td><td class="memory">1536 KB</td></tr>"""


@pytest_asyncio.fixture
async def adapter():
    instance = TimusAdapter()
    await instance._http.aclose()
    yield instance
    await instance._http.aclose()


def mock_http(adapter, handler):
    adapter._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "value",
    [
        "1000",
        " 1000 ",
        "https://acm.timus.ru/problem.aspx?space=1&num=1000",
        "HTTPS://ACM.TIMUS.RU/PROBLEM.ASPX?SPACE=1&NUM=1000",
    ],
)
def test_problem_ids(value):
    assert parse_problem_id(value) == "1000"


@pytest.mark.parametrize(
    "value",
    [
        "abc",
        "999",
        "https://evil.test/problem.aspx?num=1000",
        "https://acm.timus.ru/problem.aspx?space=2&num=1000",
    ],
)
def test_invalid_problem_ids(value):
    with pytest.raises(ValueError):
        parse_problem_id(value)


def test_author_requires_public_numeric_id():
    assert parse_author_id(" 0042 ") == "42"
    for value in ("42AB", "nickname", "0", "-1"):
        with pytest.raises(ValueError):
            parse_author_id(value)


@pytest.mark.asyncio
async def test_import_and_statements(adapter):
    def handler(request):
        assert request.url.params["num"] == "1000"
        assert request.url.params["space"] == "1"
        return httpx.Response(200, text=PROBLEM_HTML)

    mock_http(adapter, handler)
    result = await adapter.fetch_problem("1000")
    assert result.title == "A+B Problem"
    assert result.tags == ["beginners"]
    assert result.difficulty == 16
    problem = SimpleNamespace(external_id="1000", title="A+B <Problem>")
    rendered = await adapter.render_statement_html(problem)
    assert '<base href="https://acm.timus.ru/">' in rendered
    assert "A+B &lt;Problem&gt;" in rendered
    assert "Calculate a+b" in await adapter.fetch_statement_text(problem)
    assert adapter.submit_url("1", "1000").endswith("space=1&num=1000")


@pytest.mark.asyncio
async def test_status_parse_timezone_and_author_filter(adapter):
    def handler(request):
        assert request.url.params["author"] == "42"
        assert request.url.params["locale"] == "en"
        assert request.url.params["count"] == "100"
        return httpx.Response(
            200,
            text='<table class="status">'
            + status_row(author="43")
            + status_row(date="invalid")
            + status_row()
            + "</table>",
        )

    mock_http(adapter, handler)
    rows = await adapter.fetch_user_submissions("42")
    assert len(rows) == 1
    row = rows[0]
    assert row.external_id == "123"
    assert row.external_problem_id == "1000"
    assert row.submitted_at == datetime(2026, 9, 24, 16, 48, 17, tzinfo=timezone.utc)
    assert row.time_ms == 62
    assert row.memory_mb == 2
    assert row.verdict == SubmissionVerdict.accepted


@pytest.mark.parametrize(
    ("label", "verdict"),
    [
        ("Wrong answer", SubmissionVerdict.wrong_answer),
        ("Time limit exceeded", SubmissionVerdict.time_limit),
        ("Memory limit exceeded", SubmissionVerdict.memory_limit),
        ("Runtime error (access violation)", SubmissionVerdict.runtime_error),
        ("Compilation error", SubmissionVerdict.compilation_error),
        ("In queue", SubmissionVerdict.pending),
        ("Testing", SubmissionVerdict.running),
        ("Restricted function", SubmissionVerdict.rejected),
    ],
)
@pytest.mark.asyncio
async def test_verdicts(adapter, label, verdict):
    mock_http(
        adapter,
        lambda _: httpx.Response(
            200, text='<table class="status">' + status_row(verdict=label) + "</table>"
        ),
    )
    assert (await adapter.fetch_user_submissions("42"))[0].verdict == verdict


@pytest.mark.asyncio
async def test_errors_and_empty_history(adapter):
    mock_http(
        adapter, lambda _: httpx.Response(200, text='<table class="status"></table>')
    )
    assert await adapter.fetch_user_submissions("42") == []
    with pytest.raises(ValueError):
        await adapter.fetch_problem("9999")
    mock_http(adapter, lambda _: httpx.Response(503))
    with pytest.raises(RuntimeError):
        await adapter.fetch_user_submissions("42")
    mock_http(adapter, lambda _: httpx.Response(200, text="<html>Maintenance</html>"))
    with pytest.raises(RuntimeError):
        await adapter.fetch_user_submissions("42")
