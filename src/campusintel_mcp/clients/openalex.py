"""Typed adapter for the OpenAlex scholarly knowledge graph."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import httpx

from campusintel_mcp.clients.base import JsonAPIClient
from campusintel_mcp.errors import NotFoundError
from campusintel_mcp.models import InstitutionSummary, Researcher, ResearchWork, SourceRef


def _openalex_short_id(value: str) -> str:
    short = value.rstrip("/").rsplit("/", 1)[-1].upper()
    if not short or short[0] not in {"A", "I", "W"} or not short[1:].isdigit():
        raise ValueError(f"Invalid OpenAlex identifier: {value!r}")
    return short


def _source(entity_id: str) -> SourceRef:
    return SourceRef(provider="OpenAlex", url=f"https://openalex.org/{entity_id}")


class OpenAlexClient(JsonAPIClient):
    """Read institutions, authors, and scholarly works from OpenAlex."""

    def __init__(
        self,
        *,
        api_key: str | None,
        timeout_seconds: int,
        cache_ttl_seconds: int,
        max_retries: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            base_url="https://api.openalex.org",
            provider="OpenAlex",
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            max_retries=max_retries,
            http_client=http_client,
        )
        self.api_key = api_key

    def _auth(self) -> dict[str, str]:
        return {"api_key": self.api_key} if self.api_key else {}

    @staticmethod
    def _institution(item: dict[str, Any]) -> InstitutionSummary:
        entity_id = _openalex_short_id(str(item["id"]))
        geo = item.get("geo") or {}
        return InstitutionSummary(
            openalex_id=entity_id,
            name=item.get("display_name") or "Unknown institution",
            country_code=item.get("country_code"),
            institution_type=item.get("type"),
            homepage_url=item.get("homepage_url"),
            city=geo.get("city"),
            region=geo.get("region"),
            works_count=item.get("works_count") or 0,
            cited_by_count=item.get("cited_by_count") or 0,
            source=_source(entity_id),
        )

    async def search_institutions(
        self,
        query: str,
        *,
        country_code: str | None = None,
        limit: int = 10,
    ) -> list[InstitutionSummary]:
        filters = ["type:education"]
        if country_code:
            filters.append(f"country_code:{country_code.lower()}")
        payload = await self.get_json(
            "/institutions",
            {
                "search": query.strip(),
                "filter": ",".join(filters),
                "per_page": limit,
                "select": (
                    "id,display_name,country_code,type,homepage_url,geo,works_count,cited_by_count"
                ),
                **self._auth(),
            },
        )
        return [self._institution(item) for item in payload.get("results", [])]

    async def get_institution_raw(self, institution_id: str) -> dict[str, Any]:
        entity_id = _openalex_short_id(institution_id)
        payload = await self.get_json(f"/institutions/{entity_id}", self._auth())
        if not payload.get("id"):
            raise NotFoundError(f"OpenAlex institution {entity_id} was not found")
        return payload

    async def get_institution(self, institution_id: str) -> InstitutionSummary:
        return self._institution(await self.get_institution_raw(institution_id))

    @staticmethod
    def _work(item: dict[str, Any]) -> ResearchWork:
        entity_id = _openalex_short_id(str(item["id"]))
        open_access = item.get("open_access") or {}
        primary_topic = item.get("primary_topic") or {}
        authors = [
            authorship.get("author", {}).get("display_name")
            for authorship in item.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        return ResearchWork(
            openalex_id=entity_id,
            title=item.get("display_name") or item.get("title") or "Untitled work",
            publication_year=item.get("publication_year"),
            publication_date=item.get("publication_date"),
            cited_by_count=item.get("cited_by_count") or 0,
            work_type=item.get("type"),
            doi=item.get("doi"),
            is_open_access=bool(open_access.get("is_oa")),
            open_access_url=open_access.get("oa_url"),
            authors=authors,
            primary_topic=primary_topic.get("display_name"),
            source=_source(entity_id),
        )

    async def search_works(
        self,
        query: str,
        *,
        institution_id: str | None = None,
        from_year: int | None = None,
        to_year: int | None = None,
        open_access_only: bool = False,
        limit: int = 10,
    ) -> list[ResearchWork]:
        filters: list[str] = []
        if institution_id:
            filters.append(f"authorships.institutions.id:{_openalex_short_id(institution_id)}")
        if from_year:
            filters.append(f"from_publication_date:{from_year}-01-01")
        if to_year:
            filters.append(f"to_publication_date:{to_year}-12-31")
        if open_access_only:
            filters.append("open_access.is_oa:true")
        payload = await self.get_json(
            "/works",
            {
                "search": query.strip(),
                "filter": ",".join(filters) or None,
                "per_page": limit,
                "sort": "relevance_score:desc" if query.strip() else "publication_date:desc",
                "select": (
                    "id,display_name,publication_year,publication_date,cited_by_count,type,doi,"
                    "open_access,authorships,primary_topic"
                ),
                **self._auth(),
            },
        )
        return [self._work(item) for item in payload.get("results", [])]

    async def search_authors(
        self,
        query: str,
        *,
        institution_id: str | None = None,
        limit: int = 10,
    ) -> list[Researcher]:
        filters = []
        if institution_id:
            filters.append(f"last_known_institutions.id:{_openalex_short_id(institution_id)}")
        payload = await self.get_json(
            "/authors",
            {
                "search": query.strip(),
                "filter": ",".join(filters) or None,
                "per_page": limit,
                "select": "id,display_name,orcid,works_count,cited_by_count",
                **self._auth(),
            },
        )
        researchers = []
        for item in payload.get("results", []):
            entity_id = _openalex_short_id(str(item["id"]))
            researchers.append(
                Researcher(
                    openalex_id=entity_id,
                    name=item.get("display_name") or "Unknown researcher",
                    orcid=item.get("orcid"),
                    works_count=item.get("works_count"),
                    cited_by_count=item.get("cited_by_count"),
                    source=_source(entity_id),
                )
            )
        return researchers

    async def find_topic_researchers(
        self,
        topic: str,
        *,
        institution_id: str,
        limit: int = 10,
    ) -> list[Researcher]:
        institution = _openalex_short_id(institution_id)
        sample_size = min(100, max(25, limit * 8))
        payload = await self.get_json(
            "/works",
            {
                "search": topic.strip(),
                "filter": f"authorships.institutions.id:{institution}",
                "per_page": sample_size,
                "sort": "relevance_score:desc",
                "select": "id,display_name,cited_by_count,authorships",
                **self._auth(),
            },
        )
        stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"name": "", "orcid": None, "papers": 0, "citations": 0, "works": []}
        )
        for work in payload.get("results", []):
            for authorship in work.get("authorships", []):
                affiliations = authorship.get("institutions") or []
                affiliated = any(
                    _openalex_short_id(str(affiliation.get("id"))) == institution
                    for affiliation in affiliations
                    if affiliation.get("id")
                )
                author = authorship.get("author") or {}
                if not affiliated or not author.get("id"):
                    continue
                author_id = _openalex_short_id(str(author["id"]))
                entry = stats[author_id]
                entry["name"] = author.get("display_name") or "Unknown researcher"
                entry["orcid"] = author.get("orcid")
                entry["papers"] += 1
                entry["citations"] += work.get("cited_by_count") or 0
                if len(entry["works"]) < 3:
                    entry["works"].append(work.get("display_name") or "Untitled work")

        ranked = sorted(
            stats.items(),
            key=lambda pair: (pair[1]["papers"], pair[1]["citations"]),
            reverse=True,
        )[:limit]
        return [
            Researcher(
                openalex_id=author_id,
                name=data["name"],
                orcid=data["orcid"],
                relevance_papers=data["papers"],
                relevance_citations=data["citations"],
                example_works=data["works"],
                source=_source(author_id),
            )
            for author_id, data in ranked
        ]
