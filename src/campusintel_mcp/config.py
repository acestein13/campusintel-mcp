"""Environment-backed application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, cast

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _int_env(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated runtime settings."""

    openalex_api_key: str | None
    college_scorecard_api_key: str | None
    timeout_seconds: int
    cache_ttl_seconds: int
    max_retries: int
    log_level: LogLevel
    transport: str
    host: str
    port: int

    @classmethod
    def from_env(cls) -> Settings:
        transport = os.getenv("CAMPUSINTEL_TRANSPORT", "stdio").lower()
        if transport not in {"stdio", "streamable-http"}:
            raise ValueError("CAMPUSINTEL_TRANSPORT must be 'stdio' or 'streamable-http'")
        log_level = os.getenv("CAMPUSINTEL_LOG_LEVEL", "INFO").upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("CAMPUSINTEL_LOG_LEVEL is invalid")
        return cls(
            openalex_api_key=os.getenv("OPENALEX_API_KEY") or None,
            college_scorecard_api_key=os.getenv("COLLEGE_SCORECARD_API_KEY") or None,
            timeout_seconds=_int_env("CAMPUSINTEL_TIMEOUT_SECONDS", 20, 1, 120),
            cache_ttl_seconds=_int_env("CAMPUSINTEL_CACHE_TTL_SECONDS", 900, 0, 86_400),
            max_retries=_int_env("CAMPUSINTEL_MAX_RETRIES", 2, 0, 5),
            log_level=cast(LogLevel, log_level),
            transport=transport,
            host=os.getenv("CAMPUSINTEL_HOST", "127.0.0.1"),
            port=_int_env("CAMPUSINTEL_PORT", 8000, 1, 65_535),
        )
