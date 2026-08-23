from __future__ import annotations

import httpx
import pytest

from campusintel_mcp.clients.openalex import OpenAlexClient, _openalex_short_id


def make_client(handler: httpx.MockTransport) -> OpenAlexClient:
    return OpenAlexClient(
        api_key="test-key",
        timeout_seconds=5,
        cache_ttl_seconds=0,
        max_retries=0,
        http_client=httpx.AsyncClient(transport=handler),
    )


def test_openalex_id_normalization() -> None:
    assert _openalex_short_id("https://openalex.org/I136199984") == "I136199984"
    assert _openalex_short_id("w123") == "W123"
    with pytest.raises(ValueError, match="Invalid OpenAlex"):
        _openalex_short_id("Harvard")


@pytest.mark.anyio
async def test_search_institutions(institution_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["search"] == "Harvard"
        assert "country_code:us" in request.url.params["filter"]
        assert request.url.params["api_key"] == "test-key"
        return httpx.Response(200, json={"results": [institution_payload]})

    client = make_client(httpx.MockTransport(handler))
    results = await client.search_institutions("Harvard", country_code="US")
    assert results[0].openalex_id == "I136199984"
    assert results[0].city == "Cambridge"


@pytest.mark.anyio
async def test_search_works(work_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "authorships.institutions.id:I136199984" in request.url.params["filter"]
        assert "open_access.is_oa:true" in request.url.params["filter"]
        return httpx.Response(200, json={"results": [work_payload]})

    client = make_client(httpx.MockTransport(handler))
    results = await client.search_works(
        "responsible AI",
        institution_id="I136199984",
        open_access_only=True,
    )
    assert results[0].is_open_access is True
    assert results[0].authors == ["Ada Researcher"]
    assert results[0].primary_topic == "Artificial Intelligence Ethics"


@pytest.mark.anyio
async def test_find_topic_researchers(work_payload: dict[str, object]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": [work_payload, work_payload]})

    client = make_client(httpx.MockTransport(handler))
    results = await client.find_topic_researchers(
        "AI governance", institution_id="I136199984", limit=5
    )
    assert results[0].name == "Ada Researcher"
    assert results[0].relevance_papers == 2
    assert results[0].relevance_citations == 24


@pytest.mark.anyio
async def test_get_institution(institution_payload: dict[str, object]) -> None:
    client = make_client(
        httpx.MockTransport(lambda request: httpx.Response(200, json=institution_payload))
    )
    result = await client.get_institution("I136199984")
    assert result.name == "Harvard University"


@pytest.mark.anyio
async def test_search_authors() -> None:
    payload = {
        "results": [
            {
                "id": "https://openalex.org/A123",
                "display_name": "Ada Researcher",
                "orcid": "https://orcid.org/0000-0000-0000-0001",
                "works_count": 20,
                "cited_by_count": 400,
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["filter"] == "last_known_institutions.id:I136199984"
        return httpx.Response(200, json=payload)

    client = make_client(httpx.MockTransport(handler))
    result = await client.search_authors("Ada", institution_id="I136199984")
    assert result[0].works_count == 20
