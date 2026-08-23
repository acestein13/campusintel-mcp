from __future__ import annotations

import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def institution_payload() -> dict[str, object]:
    return {
        "id": "https://openalex.org/I136199984",
        "display_name": "Harvard University",
        "country_code": "US",
        "type": "education",
        "homepage_url": "https://www.harvard.edu/",
        "geo": {"city": "Cambridge", "region": "Massachusetts"},
        "works_count": 400000,
        "cited_by_count": 20000000,
        "summary_stats": {"h_index": 1200, "i10_index": 90000, "2yr_mean_citedness": 5.1},
    }


@pytest.fixture
def work_payload() -> dict[str, object]:
    return {
        "id": "https://openalex.org/W123456789",
        "display_name": "Responsible artificial intelligence in high-stakes decisions",
        "publication_year": 2026,
        "publication_date": "2026-04-15",
        "cited_by_count": 12,
        "type": "article",
        "doi": "https://doi.org/10.1000/example",
        "open_access": {"is_oa": True, "oa_url": "https://example.edu/paper"},
        "primary_topic": {"display_name": "Artificial Intelligence Ethics"},
        "authorships": [
            {
                "author": {
                    "id": "https://openalex.org/A123456789",
                    "display_name": "Ada Researcher",
                    "orcid": "https://orcid.org/0000-0000-0000-0001",
                },
                "institutions": [
                    {"id": "https://openalex.org/I136199984", "display_name": "Harvard University"}
                ],
            }
        ],
    }


@pytest.fixture
def school_payload() -> dict[str, object]:
    return {
        "id": 166027,
        "school.name": "Harvard University",
        "school.city": "Cambridge",
        "school.state": "MA",
        "school.school_url": "www.harvard.edu",
        "latest.student.size": 8756,
        "latest.admissions.admission_rate.overall": 0.032,
        "latest.cost.avg_net_price.overall": 18500,
        "latest.completion.rate_suppressed.overall": 0.97,
        "latest.earnings.10_yrs_after_entry.median": 95000,
        "latest.cost.tuition.in_state": 59000,
        "latest.cost.tuition.out_of_state": 59000,
    }
