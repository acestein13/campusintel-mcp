"""CampusIntel Model Context Protocol server."""

from __future__ import annotations

from mcp.server import MCPServer

from campusintel_mcp.clients import CollegeScorecardClient, OpenAlexClient
from campusintel_mcp.config import Settings
from campusintel_mcp.models import (
    AcademicProgram,
    InstitutionProfile,
    InstitutionSummary,
    Researcher,
    ResearchWork,
    SchoolMetrics,
    UniversityComparison,
)
from campusintel_mcp.service import CampusIntelService

settings = Settings.from_env()

openalex = OpenAlexClient(
    api_key=settings.openalex_api_key,
    timeout_seconds=settings.timeout_seconds,
    cache_ttl_seconds=settings.cache_ttl_seconds,
    max_retries=settings.max_retries,
)
scorecard = CollegeScorecardClient(
    api_key=settings.college_scorecard_api_key,
    timeout_seconds=settings.timeout_seconds,
    cache_ttl_seconds=settings.cache_ttl_seconds,
    max_retries=settings.max_retries,
)
service = CampusIntelService(openalex, scorecard)

mcp = MCPServer(
    "CampusIntel",
    instructions=(
        "Use OpenAlex institution IDs returned by search_universities for research tools. "
        "Use College Scorecard IDs returned by search_us_colleges for program tools. "
        "Preserve source links and data notes in any answer. Never present descriptive metrics "
        "as admissions predictions or university rankings."
    ),
    log_level=settings.log_level,
)


def _limit(value: int, *, maximum: int = 100) -> int:
    if not 1 <= value <= maximum:
        raise ValueError(f"limit must be between 1 and {maximum}")
    return value


@mcp.tool()
async def search_universities(
    query: str,
    country_code: str | None = None,
    limit: int = 10,
) -> list[InstitutionSummary]:
    """Find universities worldwide and return stable OpenAlex IDs for later research calls.

    Args:
        query: Full or partial university name.
        country_code: Optional two-letter ISO country code, such as US or GB.
        limit: Number of results from 1 to 25.
    """
    if not query.strip():
        raise ValueError("query cannot be empty")
    if country_code and (len(country_code) != 2 or not country_code.isalpha()):
        raise ValueError("country_code must be a two-letter ISO code")
    return await openalex.search_institutions(
        query,
        country_code=country_code,
        limit=_limit(limit, maximum=25),
    )


@mcp.tool()
async def get_university_profile(institution_id: str) -> InstitutionProfile:
    """Get an institution profile with research metrics and optional U.S. federal data.

    Args:
        institution_id: OpenAlex institution ID, such as I136199984.
    """
    return await service.institution_profile(institution_id)


@mcp.tool()
async def search_research(
    topic: str,
    institution_id: str | None = None,
    from_year: int | None = None,
    to_year: int | None = None,
    open_access_only: bool = False,
    limit: int = 10,
) -> list[ResearchWork]:
    """Search scholarly works by topic, optionally scoped to a university and date range.

    Args:
        topic: Keywords or a research question.
        institution_id: Optional OpenAlex institution ID.
        from_year: Optional first publication year.
        to_year: Optional last publication year.
        open_access_only: Return only works OpenAlex marks as open access.
        limit: Number of works from 1 to 50.
    """
    if not topic.strip():
        raise ValueError("topic cannot be empty")
    if from_year and to_year and from_year > to_year:
        raise ValueError("from_year cannot be later than to_year")
    for year in (from_year, to_year):
        if year is not None and not 1600 <= year <= 2100:
            raise ValueError("years must be between 1600 and 2100")
    return await openalex.search_works(
        topic,
        institution_id=institution_id,
        from_year=from_year,
        to_year=to_year,
        open_access_only=open_access_only,
        limit=_limit(limit, maximum=50),
    )


@mcp.tool()
async def search_researchers(
    name: str,
    institution_id: str | None = None,
    limit: int = 10,
) -> list[Researcher]:
    """Find researchers by name, optionally scoped to a last-known university affiliation.

    Args:
        name: Researcher name or partial name.
        institution_id: Optional OpenAlex institution ID.
        limit: Number of researchers from 1 to 25.
    """
    if not name.strip():
        raise ValueError("name cannot be empty")
    return await openalex.search_authors(
        name,
        institution_id=institution_id,
        limit=_limit(limit, maximum=25),
    )


@mcp.tool()
async def find_topic_researchers(
    topic: str,
    institution_id: str,
    limit: int = 10,
) -> list[Researcher]:
    """Identify researchers connected to a topic at one university using matching works.

    Results are ranked by matching paper count, then citations within the returned sample. This
    is a discovery aid, not an exhaustive faculty directory or quality ranking.

    Args:
        topic: Research topic or keywords.
        institution_id: OpenAlex institution ID.
        limit: Number of researchers from 1 to 25.
    """
    if not topic.strip():
        raise ValueError("topic cannot be empty")
    return await openalex.find_topic_researchers(
        topic,
        institution_id=institution_id,
        limit=_limit(limit, maximum=25),
    )


@mcp.tool()
async def search_us_colleges(
    query: str,
    state: str | None = None,
    limit: int = 10,
) -> list[SchoolMetrics]:
    """Find U.S. colleges and return federal College Scorecard metrics and IDs.

    Args:
        query: Full or partial institution name.
        state: Optional two-letter U.S. state abbreviation.
        limit: Number of results from 1 to 25.
    """
    if not query.strip():
        raise ValueError("query cannot be empty")
    if state and (len(state) != 2 or not state.isalpha()):
        raise ValueError("state must be a two-letter abbreviation")
    return await scorecard.search_schools(query, state=state, limit=_limit(limit, maximum=25))


@mcp.tool()
async def list_academic_programs(
    school_id: int,
    query: str | None = None,
    credential_level: int | None = None,
    limit: int = 25,
) -> list[AcademicProgram]:
    """List College Scorecard fields of study for one U.S. institution.

    Args:
        school_id: College Scorecard school ID returned by search_us_colleges.
        query: Optional case-insensitive title filter, such as computer science.
        credential_level: Optional federal credential code from 1 through 8.
        limit: Number of programs from 1 to 100.
    """
    if school_id <= 0:
        raise ValueError("school_id must be positive")
    if credential_level is not None and credential_level not in range(1, 9):
        raise ValueError("credential_level must be between 1 and 8")
    return await scorecard.list_programs(
        school_id,
        query=query,
        credential_level=credential_level,
        limit=_limit(limit),
    )


@mcp.tool()
async def compare_universities(institution_ids: list[str]) -> UniversityComparison:
    """Compare two to five universities with source-aware research and U.S. federal metrics.

    Args:
        institution_ids: Two to five OpenAlex institution IDs.
    """
    if not 2 <= len(institution_ids) <= 5:
        raise ValueError("provide between two and five institution_ids")
    if len(set(institution_ids)) != len(institution_ids):
        raise ValueError("institution_ids must be unique")
    return await service.compare_institutions(institution_ids)


@mcp.tool()
async def health_check() -> dict[str, object]:
    """Report server and provider configuration without making external requests."""
    return await service.health()


@mcp.resource("campusintel://methodology")
def methodology() -> str:
    """Explain sources, entity identifiers, limitations, and responsible use."""
    return """# CampusIntel methodology

- Scholarly works, authors, affiliations, and research metrics come from OpenAlex.
- U.S. institution, cost, admissions, completion, earnings, and field-of-study data come from the
  U.S. Department of Education College Scorecard.
- Use OpenAlex institution IDs for research tools and College Scorecard IDs for program tools.
- Provider coverage, matching, and reporting cohorts can create missing or non-comparable values.
- Citation counts describe an indexed scholarly corpus. They are not measures of teaching quality,
  admissions probability, researcher worth, or overall university quality.
- College Scorecard `latest` fields can come from different reporting cohorts. Preserve nulls and
  source links, and verify consequential claims with the linked provider record.
"""


@mcp.prompt()
def research_university_fit(student_interests: str, priorities: str = "") -> str:
    """Create a source-grounded workflow for investigating university research fit."""
    return f"""Investigate university research fit for these interests: {student_interests}.
Additional priorities: {priorities or "none provided"}.

Use CampusIntel in this order:
1. Resolve every university with search_universities and retain its OpenAlex ID.
2. Use search_research and find_topic_researchers for each institution.
3. Use get_university_profile for context, not a ranking.
4. For U.S. program data, resolve a College Scorecard ID with search_us_colleges, then call
   list_academic_programs.
5. Cite the returned source URLs, distinguish missing data from zero, and state limitations.
"""


def main() -> None:
    """Run CampusIntel over the configured MCP transport."""
    if settings.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=settings.host, port=settings.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
