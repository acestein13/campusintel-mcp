"""Stable, source-aware output models returned by CampusIntel tools."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    provider: str
    url: str
    note: str | None = None


class InstitutionSummary(BaseModel):
    openalex_id: str
    name: str
    country_code: str | None = None
    institution_type: str | None = None
    homepage_url: str | None = None
    city: str | None = None
    region: str | None = None
    works_count: int = 0
    cited_by_count: int = 0
    source: SourceRef


class SchoolMetrics(BaseModel):
    scorecard_id: int
    name: str
    city: str | None = None
    state: str | None = None
    website: str | None = None
    student_size: int | None = None
    admission_rate: float | None = None
    average_net_price: int | None = None
    completion_rate: float | None = None
    median_earnings_10yr: int | None = None
    in_state_tuition: int | None = None
    out_of_state_tuition: int | None = None
    source: SourceRef


class InstitutionProfile(BaseModel):
    institution: InstitutionSummary
    research_impact_h_index: int | None = None
    research_impact_i10_index: int | None = None
    two_year_mean_citedness: float | None = None
    scorecard: SchoolMetrics | None = None
    data_notes: list[str] = Field(default_factory=list)


class ResearchWork(BaseModel):
    openalex_id: str
    title: str
    publication_year: int | None = None
    publication_date: str | None = None
    cited_by_count: int = 0
    work_type: str | None = None
    doi: str | None = None
    is_open_access: bool = False
    open_access_url: str | None = None
    authors: list[str] = Field(default_factory=list)
    primary_topic: str | None = None
    source: SourceRef


class Researcher(BaseModel):
    openalex_id: str
    name: str
    orcid: str | None = None
    works_count: int | None = None
    cited_by_count: int | None = None
    relevance_papers: int | None = None
    relevance_citations: int | None = None
    example_works: list[str] = Field(default_factory=list)
    source: SourceRef


class AcademicProgram(BaseModel):
    cip_code: str
    title: str
    credential_level: int
    credential_name: str
    graduates_count: int | None = None
    median_earnings: int | None = None
    median_debt: int | None = None
    source: SourceRef


class UniversityComparison(BaseModel):
    profiles: list[InstitutionProfile]
    methodology: list[str]
    generated_from_live_data: bool = True
