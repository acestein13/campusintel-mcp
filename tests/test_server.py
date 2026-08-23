from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from mcp import Client

import campusintel_mcp.server as server
from campusintel_mcp.models import (
    InstitutionProfile,
    InstitutionSummary,
    SourceRef,
    UniversityComparison,
)

mcp = server.mcp


@pytest.mark.anyio
async def test_server_advertises_expected_capabilities() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert {
            "search_universities",
            "get_university_profile",
            "search_research",
            "search_researchers",
            "find_topic_researchers",
            "search_us_colleges",
            "list_academic_programs",
            "compare_universities",
            "health_check",
        } <= names


@pytest.mark.anyio
async def test_health_check_does_not_expose_secrets() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.call_tool("health_check", {})
        text = result.content[0].text
        payload = json.loads(text)
        assert payload["status"] == "ok"
        assert "test-key" not in text


@pytest.mark.anyio
async def test_methodology_resource() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        result = await client.read_resource("campusintel://methodology")
        assert "not measures of teaching quality" in result.contents[0].text


@pytest.mark.anyio
async def test_data_tools_delegate_to_provider_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    search_institutions = AsyncMock(return_value=[])
    search_works = AsyncMock(return_value=[])
    search_authors = AsyncMock(return_value=[])
    topic_researchers = AsyncMock(return_value=[])
    search_schools = AsyncMock(return_value=[])
    list_programs = AsyncMock(return_value=[])
    profile_result = InstitutionProfile(
        institution=InstitutionSummary(
            openalex_id="I1",
            name="Example University",
            source=SourceRef(provider="OpenAlex", url="https://openalex.org/I1"),
        )
    )
    profile = AsyncMock(return_value=profile_result)
    comparison = AsyncMock(return_value=UniversityComparison(profiles=[], methodology=["test"]))
    monkeypatch.setattr(server.openalex, "search_institutions", search_institutions)
    monkeypatch.setattr(server.openalex, "search_works", search_works)
    monkeypatch.setattr(server.openalex, "search_authors", search_authors)
    monkeypatch.setattr(server.openalex, "find_topic_researchers", topic_researchers)
    monkeypatch.setattr(server.scorecard, "search_schools", search_schools)
    monkeypatch.setattr(server.scorecard, "list_programs", list_programs)
    monkeypatch.setattr(server.service, "institution_profile", profile)
    monkeypatch.setattr(server.service, "compare_institutions", comparison)

    async with Client(mcp, raise_exceptions=True) as client:
        await client.call_tool(
            "search_universities", {"query": "Harvard", "country_code": "US", "limit": 3}
        )
        await client.call_tool(
            "search_research",
            {
                "topic": "AI safety",
                "institution_id": "I1",
                "from_year": 2020,
                "to_year": 2026,
                "open_access_only": True,
                "limit": 4,
            },
        )
        await client.call_tool(
            "search_researchers", {"name": "Ada", "institution_id": "I1", "limit": 5}
        )
        await client.call_tool(
            "find_topic_researchers", {"topic": "AI", "institution_id": "I1", "limit": 5}
        )
        await client.call_tool(
            "search_us_colleges", {"query": "Harvard", "state": "MA", "limit": 5}
        )
        await client.call_tool(
            "list_academic_programs",
            {"school_id": 166027, "query": "computer", "credential_level": 3, "limit": 5},
        )
        await client.call_tool("get_university_profile", {"institution_id": "I1"})
        await client.call_tool("compare_universities", {"institution_ids": ["I1", "I2"]})

    search_institutions.assert_awaited_once()
    search_works.assert_awaited_once()
    comparison.assert_awaited_once()


@pytest.mark.anyio
async def test_tool_validation_errors_are_visible() -> None:
    async with Client(mcp, raise_exceptions=True) as client:
        empty = await client.call_tool("search_universities", {"query": ""})
        years = await client.call_tool(
            "search_research", {"topic": "AI", "from_year": 2026, "to_year": 2020}
        )
        comparison = await client.call_tool("compare_universities", {"institution_ids": ["I1"]})
        assert empty.is_error is True
        assert "query cannot be empty" in empty.content[0].text
        assert years.is_error is True
        assert "from_year" in years.content[0].text
        assert comparison.is_error is True
        assert "two and five" in comparison.content[0].text
