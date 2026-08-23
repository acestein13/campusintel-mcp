from __future__ import annotations

import httpx
import pytest

from campusintel_mcp.clients.base import JsonAPIClient
from campusintel_mcp.errors import UpstreamAPIError


def client(transport: httpx.MockTransport, *, ttl: int = 0, retries: int = 0) -> JsonAPIClient:
    return JsonAPIClient(
        base_url="https://example.test",
        provider="Example",
        timeout_seconds=1,
        cache_ttl_seconds=ttl,
        max_retries=retries,
        http_client=httpx.AsyncClient(transport=transport),
    )


@pytest.mark.anyio
async def test_successful_response_is_cached() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"value": calls})

    api = client(httpx.MockTransport(handler), ttl=60)
    first = await api.get_json("/data", {"q": "same"})
    second = await api.get_json("/data", {"q": "same", "unused": None})
    assert first == second == {"value": 1}
    assert calls == 1


@pytest.mark.anyio
async def test_transient_status_is_retried() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"ok": True})

    api = client(httpx.MockTransport(handler), retries=1)
    assert await api.get_json("/data", {}) == {"ok": True}
    assert calls == 2


@pytest.mark.anyio
async def test_authentication_error_is_actionable() -> None:
    api = client(httpx.MockTransport(lambda request: httpx.Response(401, json={})))
    with pytest.raises(UpstreamAPIError, match="authentication was rejected"):
        await api.get_json("/data", {})


@pytest.mark.anyio
async def test_non_object_json_is_rejected() -> None:
    api = client(httpx.MockTransport(lambda request: httpx.Response(200, json=[1, 2])))
    with pytest.raises(UpstreamAPIError, match="unexpected response shape"):
        await api.get_json("/data", {})
