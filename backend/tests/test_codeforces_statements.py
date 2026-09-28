from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
import pytest_asyncio

from app.core.security import create_access_token
from app.integrations.judges import codeforces, registry
from app.models.enums import ExternalSource, UserRole
from app.models.problem import Problem
from app.models.user import User

PROBLEM = SimpleNamespace(
    external_id="1472A", title="Cards <for> Friends",
    external_url="https://codeforces.com/problemset/problem/1472/A",
)
STATEMENT = '<div class="problem-statement"><p>Открытки для друзей</p><pre>1 2 3</pre></div>'


@pytest_asyncio.fixture
async def adapter():
    instance = codeforces.CodeforcesAdapter()
    await instance._http.aclose()
    yield instance
    await instance._http.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [403, 429, 503, "timeout", "challenge", "empty"])
async def test_fallback_and_shared_cache(adapter, failure):
    hosts = []

    def handler(request):
        hosts.append(request.url.host)
        assert request.url.path == "/problemset/problem/1472/A"
        assert request.url.params["locale"] == "ru"
        if request.url.host == "codeforces.com":
            if failure == "timeout":
                raise httpx.ReadTimeout("unavailable", request=request)
            if failure == "challenge":
                return httpx.Response(200, text="<script>challenge()</script>Please wait")
            if failure == "empty":
                return httpx.Response(200, text='<div class="problem-statement"></div>')
            return httpx.Response(failure)
        return httpx.Response(200, text="<nav>Navigation</nav>" + STATEMENT)

    adapter._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    rendered = await adapter.render_statement_html(PROBLEM)
    assert STATEMENT in rendered
    assert "Navigation" not in rendered
    assert "challenge()" not in rendered
    assert "Cards &lt;for&gt; Friends" in rendered
    assert "MathJax" in rendered
    assert "Открытки для друзей" in await adapter.fetch_statement_text(PROBLEM)
    assert await adapter.render_statement_html(PROBLEM) == rendered
    assert hosts == ["codeforces.com", "mirror.codeforces.com"]


@pytest.mark.asyncio
async def test_failures_are_not_cached_or_rendered(adapter):
    calls = []

    def handler(request):
        calls.append(request.url.host)
        return httpx.Response(200, text="<html>Please wait. Your browser is being checked.</html>")

    adapter._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(RuntimeError, match="temporarily unavailable"):
        await adapter.render_statement_html(PROBLEM)
    assert await adapter.fetch_statement_text(PROBLEM) is None
    assert calls == list(codeforces._STATEMENT_HOSTS) * 2
    assert not adapter._statement_cache


@pytest.mark.asyncio
async def test_redirects_and_cache_expiration(adapter, monkeypatch):
    now = 0
    monkeypatch.setattr(codeforces.time, "monotonic", lambda: now)
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path.startswith("/problemset"):
            return httpx.Response(302, headers={"Location": "/contest/1472/problem/A?locale=ru"})
        return httpx.Response(200, text=STATEMENT)

    adapter._http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await adapter.render_statement_html(PROBLEM)
    now = codeforces._STATEMENT_TTL + 1
    await adapter.render_statement_html(PROBLEM)
    assert len(calls) == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("error", [
    RuntimeError("upstream details"),
    httpx.ConnectError("private connection details"),
    httpx.HTTPStatusError("blocked", request=httpx.Request("GET", PROBLEM.external_url), response=httpx.Response(403)),
])
async def test_statement_api_returns_actionable_502(client, session, monkeypatch, error):
    user = User(username="reader", role=UserRole.student, hashed_password="unused")
    problem = Problem(external_source=ExternalSource.codeforces, **vars(PROBLEM))
    session.add_all([user, problem])
    await session.commit()
    statement = AsyncMock(side_effect=error)
    monkeypatch.setattr(registry, "get", lambda source: SimpleNamespace(render_statement_html=statement))
    response = await client.get(
        f"/api/v1/problems/{problem.id}/statement",
        headers={"Authorization": "Bearer " + create_access_token(user.id)},
    )
    assert response.status_code == 502
    assert "откройте оригинал" in response.json()["detail"]
    assert str(error) not in response.text
