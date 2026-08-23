from __future__ import annotations

import httpx
import pytest

from campusintel_mcp.clients.scorecard import CollegeScorecardClient
from campusintel_mcp.errors import ConfigurationError


def make_client(
    handler: httpx.MockTransport, api_key: str | None = "test-key"
) -> CollegeScorecardClient:
    return CollegeScorecardClient(
        api_key=api_key,
        timeout_seconds=5,
        cache_ttl_seconds=0,
        max_retries=0,
        http_client=httpx.AsyncClient(transport=handler),
    )


@pytest.mark.anyio
async def test_api_key_is_required() -> None:
    client = make_client(httpx.MockTransport(lambda request: httpx.Response(500)), api_key=None)
    with pytest.raises(ConfigurationError, match="COLLEGE_SCORECARD_API_KEY"):
        await client.search_schools("Harvard")


@pytest.mark.anyio
async def test_search_schools(school_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["school.state"] == "MA"
        assert request.url.params["api_key"] == "test-key"
        return httpx.Response(200, json={"results": [school_payload]})

    client = make_client(httpx.MockTransport(handler))
    results = await client.search_schools("Harvard", state="ma")
    assert results[0].scorecard_id == 166027
    assert results[0].admission_rate == 0.032


@pytest.mark.anyio
async def test_programs_are_filtered_locally() -> None:
    payload = {
        "results": [
            {
                "id": 166027,
                "school.name": "Harvard University",
                "latest.programs.cip_4_digit": [
                    {
                        "code": "1107",
                        "title": "Computer Science",
                        "credential.level": 3,
                        "counts.ipeds_awards1": 250,
                    },
                    {"code": "1601", "title": "Linguistics", "credential.level": 3},
                ],
            }
        ]
    }
    client = make_client(httpx.MockTransport(lambda request: httpx.Response(200, json=payload)))
    results = await client.list_programs(166027, query="computer", credential_level=3)
    assert len(results) == 1
    assert results[0].title == "Computer Science"
    assert results[0].credential_name == "Bachelor's degree"


@pytest.mark.anyio
async def test_get_school(school_payload: dict[str, object]) -> None:
    client = make_client(
        httpx.MockTransport(lambda request: httpx.Response(200, json={"results": [school_payload]}))
    )
    result = await client.get_school(166027)
    assert result.name == "Harvard University"


@pytest.mark.anyio
async def test_get_school_not_found() -> None:
    client = make_client(
        httpx.MockTransport(lambda request: httpx.Response(200, json={"results": []}))
    )
    from campusintel_mcp.errors import NotFoundError

    with pytest.raises(NotFoundError):
        await client.get_school(999999)
