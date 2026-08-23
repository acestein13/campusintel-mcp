"""Provider orchestration and cross-source entity enrichment."""

from __future__ import annotations

import asyncio
from typing import Any

from campusintel_mcp.clients import CollegeScorecardClient, OpenAlexClient
from campusintel_mcp.errors import ConfigurationError
from campusintel_mcp.models import InstitutionProfile, UniversityComparison


class CampusIntelService:
    """Combine scholarly and federal institution data without hiding provenance."""

    def __init__(self, openalex: OpenAlexClient, scorecard: CollegeScorecardClient) -> None:
        self.openalex = openalex
        self.scorecard = scorecard

    async def institution_profile(self, institution_id: str) -> InstitutionProfile:
        raw = await self.openalex.get_institution_raw(institution_id)
        institution = self.openalex._institution(raw)
        summary = raw.get("summary_stats") or {}
        scorecard = None
        notes = [
            "Research counts and impact metrics come from OpenAlex and reflect its indexed corpus.",
            "Counts are descriptive, not a ranking or measure of educational quality.",
        ]
        if institution.country_code == "US":
            try:
                matches = await self.scorecard.search_schools(institution.name, limit=5)
                if matches:
                    exact = next(
                        (
                            school
                            for school in matches
                            if school.name.casefold() == institution.name.casefold()
                        ),
                        matches[0],
                    )
                    scorecard = exact
                    notes.append(
                        "The College Scorecard record was name-matched; verify the source link "
                        "before using the figures in a consequential decision."
                    )
            except ConfigurationError:
                notes.append(
                    "College Scorecard enrichment is unavailable until "
                    "COLLEGE_SCORECARD_API_KEY is configured."
                )
        else:
            notes.append("College Scorecard data is available only for U.S. institutions.")

        return InstitutionProfile(
            institution=institution,
            research_impact_h_index=summary.get("h_index"),
            research_impact_i10_index=summary.get("i10_index"),
            two_year_mean_citedness=summary.get("2yr_mean_citedness"),
            scorecard=scorecard,
            data_notes=notes,
        )

    async def compare_institutions(self, institution_ids: list[str]) -> UniversityComparison:
        profiles = await asyncio.gather(
            *(self.institution_profile(institution_id) for institution_id in institution_ids)
        )
        return UniversityComparison(
            profiles=list(profiles),
            methodology=[
                "OpenAlex IDs are used as canonical institution identifiers.",
                "OpenAlex research metrics are corpus-dependent and should not be treated "
                "as rankings.",
                "U.S. College Scorecard values use each field's latest available reporting cohort; "
                "those cohorts may differ by metric.",
                "Missing values remain null rather than being estimated.",
            ],
        )

    async def health(self) -> dict[str, Any]:
        """Report local configuration without exposing secret values."""
        return {
            "status": "ok",
            "providers": {
                "openalex": {
                    "configured": True,
                    "api_key_configured": bool(self.openalex.api_key),
                },
                "college_scorecard": {
                    "configured": bool(self.scorecard.api_key),
                    "api_key_configured": bool(self.scorecard.api_key),
                },
            },
        }
