from __future__ import annotations

import pytest

from campusintel_mcp.config import Settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "OPENALEX_API_KEY",
        "COLLEGE_SCORECARD_API_KEY",
        "CAMPUSINTEL_TIMEOUT_SECONDS",
        "CAMPUSINTEL_CACHE_TTL_SECONDS",
        "CAMPUSINTEL_MAX_RETRIES",
        "CAMPUSINTEL_LOG_LEVEL",
        "CAMPUSINTEL_TRANSPORT",
        "CAMPUSINTEL_HOST",
        "CAMPUSINTEL_PORT",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = Settings.from_env()
    assert settings.transport == "stdio"
    assert settings.port == 8000
    assert settings.openalex_api_key is None


def test_settings_reject_invalid_transport(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAMPUSINTEL_TRANSPORT", "websocket")
    with pytest.raises(ValueError, match="CAMPUSINTEL_TRANSPORT"):
        Settings.from_env()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("CAMPUSINTEL_TIMEOUT_SECONDS", "slow"),
        ("CAMPUSINTEL_PORT", "70000"),
        ("CAMPUSINTEL_LOG_LEVEL", "VERBOSE"),
    ],
)
def test_settings_reject_invalid_values(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValueError):
        Settings.from_env()
