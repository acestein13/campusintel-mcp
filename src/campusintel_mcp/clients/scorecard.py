"""Typed adapter for the U.S. Department of Education College Scorecard API."""

from __future__ import annotations

from typing import Any

import httpx

from campusintel_mcp.clients.base import JsonAPIClient
from campusintel_mcp.errors import ConfigurationError, NotFoundError
from campusintel_mcp.models import AcademicProgram, SchoolMetrics, SourceRef

SCHOOL_FIELDS = [
    "id",
    "school.name",
    "school.city",
    "school.state",
    "school.school_url",
    "latest.student.size",
    "latest.admissions.admission_rate.overall",
    "latest.cost.avg_net_price.overall",
    "latest.completion.rate_suppressed.overall",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
]

CREDENTIAL_NAMES = {
    1: "Undergraduate certificate",
    2: "Associate degree",
    3: "Bachelor's degree",
    4: "Post-baccalaureate certificate",
    5: "Master's degree",
    6: "Doctoral degree",
    7: "First professional degree",
    8: "Graduate or professional certificate",
}


def _scorecard_source(school_id: int) -> SourceRef:
    return SourceRef(
        provider="U.S. Department of Education College Scorecard",
        url=f"https://collegescorecard.ed.gov/school/?{school_id}",
        note="Latest fields can represent different reporting cohorts.",
    )


class CollegeScorecardClient(JsonAPIClient):
    """Read U.S. institution and field-of-study data from College Scorecard."""

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
            base_url="https://api.data.gov/ed/collegescorecard/v1",
            provider="College Scorecard",
            timeout_seconds=timeout_seconds,
            cache_ttl_seconds=cache_ttl_seconds,
            max_retries=max_retries,
            http_client=http_client,
        )
        self.api_key = api_key

    def _auth(self) -> dict[str, str]:
        if not self.api_key:
            raise ConfigurationError(
                "COLLEGE_SCORECARD_API_KEY is required for U.S. institutional and program data. "
                "Request a free key at https://api.data.gov/signup/."
            )
        return {"api_key": self.api_key}

    @staticmethod
    def _school(item: dict[str, Any]) -> SchoolMetrics:
        school_id = int(item["id"])
        return SchoolMetrics(
            scorecard_id=school_id,
            name=item.get("school.name") or "Unknown institution",
            city=item.get("school.city"),
            state=item.get("school.state"),
            website=item.get("school.school_url"),
            student_size=item.get("latest.student.size"),
            admission_rate=item.get("latest.admissions.admission_rate.overall"),
            average_net_price=item.get("latest.cost.avg_net_price.overall"),
            completion_rate=item.get("latest.completion.rate_suppressed.overall"),
            median_earnings_10yr=item.get("latest.earnings.10_yrs_after_entry.median"),
            in_state_tuition=item.get("latest.cost.tuition.in_state"),
            out_of_state_tuition=item.get("latest.cost.tuition.out_of_state"),
            source=_scorecard_source(school_id),
        )

    async def search_schools(
        self,
        query: str,
        *,
        state: str | None = None,
        limit: int = 10,
    ) -> list[SchoolMetrics]:
        params: dict[str, Any] = {
            "school.name": query.strip(),
            "school.operating": 1,
            "fields": ",".join(SCHOOL_FIELDS),
            "per_page": limit,
            **self._auth(),
        }
        if state:
            params["school.state"] = state.upper()
        payload = await self.get_json("/schools.json", params)
        return [self._school(item) for item in payload.get("results", [])]

    async def get_school(self, school_id: int) -> SchoolMetrics:
        payload = await self.get_json(
            "/schools.json",
            {"id": school_id, "fields": ",".join(SCHOOL_FIELDS), **self._auth()},
        )
        results = payload.get("results", [])
        if not results:
            raise NotFoundError(f"College Scorecard school {school_id} was not found")
        return self._school(results[0])

    @staticmethod
    def _program_value(item: dict[str, Any], name: str) -> Any:
        for key in (
            name,
            f"cip_4_digit.{name}",
            f"latest.programs.cip_4_digit.{name}",
        ):
            if key in item:
                return item[key]
        return None

    async def list_programs(
        self,
        school_id: int,
        *,
        query: str | None = None,
        credential_level: int | None = None,
        limit: int = 25,
    ) -> list[AcademicProgram]:
        fields = "id,school.name,latest.programs.cip_4_digit"
        payload = await self.get_json(
            "/schools.json",
            {"id": school_id, "fields": fields, **self._auth()},
        )
        results = payload.get("results", [])
        if not results:
            raise NotFoundError(f"College Scorecard school {school_id} was not found")
        raw_programs = results[0].get("latest.programs.cip_4_digit") or []
        programs: list[AcademicProgram] = []
        normalized_query = (query or "").strip().casefold()
        for item in raw_programs:
            title = str(self._program_value(item, "title") or "Unknown program")
            level_raw = self._program_value(item, "credential.level")
            if level_raw is None:
                level_raw = self._program_value(item, "credential_level")
            try:
                level = int(level_raw)
            except (TypeError, ValueError):
                continue
            if credential_level is not None and level != credential_level:
                continue
            if normalized_query and normalized_query not in title.casefold():
                continue
            code = str(self._program_value(item, "code") or "")
            programs.append(
                AcademicProgram(
                    cip_code=code,
                    title=title,
                    credential_level=level,
                    credential_name=CREDENTIAL_NAMES.get(level, f"Credential level {level}"),
                    graduates_count=self._program_value(item, "counts.ipeds_awards1"),
                    median_earnings=self._program_value(
                        item, "earnings.highest.3_yr.overall_median_earnings"
                    ),
                    median_debt=self._program_value(item, "debt.all.all_inst.median"),
                    source=_scorecard_source(school_id),
                )
            )
        programs.sort(key=lambda program: (program.title.casefold(), program.credential_level))
        return programs[:limit]
