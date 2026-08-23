from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from campusintel_mcp.errors import ConfigurationError
from campusintel_mcp.models import SchoolMetrics, SourceRef
from campusintel_mcp.service import CampusIntelService


@pytest.mark.anyio
async def test_profile_enriches_us_institution(
    institution_payload: dict[str, object], school_payload: dict[str, object]
) -> None:
    openalex = AsyncMock()
    openalex.get_institution_raw.return_value = institution_payload
    from campusintel_mcp.clients.openalex import OpenAlexClient

    openalex._institution = OpenAlexClient._institution
    scorecard = AsyncMock()
    scorecard.search_schools.return_value = [
        SchoolMetrics(
            scorecard_id=166027,
            name="Harvard University",
            source=SourceRef(provider="College Scorecard", url="https://example.test"),
        )
    ]
    profile = await CampusIntelService(openalex, scorecard).institution_profile("I136199984")
    assert profile.research_impact_h_index == 1200
    assert profile.scorecard is not None
    assert profile.scorecard.scorecard_id == 166027


@pytest.mark.anyio
async def test_profile_degrades_without_scorecard_key(
    institution_payload: dict[str, object],
) -> None:
    openalex = AsyncMock()
    openalex.get_institution_raw.return_value = institution_payload
    from campusintel_mcp.clients.openalex import OpenAlexClient

    openalex._institution = OpenAlexClient._institution
    scorecard = AsyncMock()
    scorecard.search_schools.side_effect = ConfigurationError("missing")
    profile = await CampusIntelService(openalex, scorecard).institution_profile("I136199984")
    assert profile.scorecard is None
    assert any("unavailable" in note for note in profile.data_notes)


@pytest.mark.anyio
async def test_compare_and_health(institution_payload: dict[str, object]) -> None:
    openalex = AsyncMock()
    openalex.get_institution_raw.return_value = institution_payload
    openalex.api_key = "configured"
    from campusintel_mcp.clients.openalex import OpenAlexClient

    openalex._institution = OpenAlexClient._institution
    scorecard = AsyncMock()
    scorecard.api_key = "configured"
    scorecard.search_schools.return_value = []
    service = CampusIntelService(openalex, scorecard)
    comparison = await service.compare_institutions(["I1", "I2"])
    health = await service.health()
    assert len(comparison.profiles) == 2
    assert health["providers"]["openalex"]["api_key_configured"] is True
