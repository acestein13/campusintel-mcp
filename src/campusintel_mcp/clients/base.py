"""Resilient asynchronous JSON client with bounded retries and TTL caching."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

import httpx

from campusintel_mcp.errors import UpstreamAPIError


@dataclass(slots=True)
class _CacheEntry:
    expires_at: float
    value: dict[str, Any]


class JsonAPIClient:
    """Small HTTP foundation shared by provider-specific clients."""

    RETRYABLE_STATUS_CODES: ClassVar[set[int]] = {429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        base_url: str,
        provider: str,
        timeout_seconds: int,
        cache_ttl_seconds: int,
        max_retries: int,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.provider = provider
        self.cache_ttl_seconds = cache_ttl_seconds
        self.max_retries = max_retries
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
            headers={"Accept": "application/json", "User-Agent": "campusintel-mcp/1.0"},
        )
        self._cache: dict[str, _CacheEntry] = {}
        self._cache_lock = asyncio.Lock()

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    @staticmethod
    def _cache_key(path: str, params: Mapping[str, Any]) -> str:
        encoded = json.dumps([path, sorted(params.items())], separators=(",", ":"), default=str)
        return hashlib.sha256(encoded.encode()).hexdigest()

    async def _cached(self, key: str) -> dict[str, Any] | None:
        if self.cache_ttl_seconds == 0:
            return None
        async with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                self._cache.pop(key, None)
                return None
            return entry.value

    async def _store(self, key: str, value: dict[str, Any]) -> None:
        if self.cache_ttl_seconds == 0:
            return
        async with self._cache_lock:
            self._cache[key] = _CacheEntry(
                expires_at=time.monotonic() + self.cache_ttl_seconds,
                value=value,
            )

    async def get_json(self, path: str, params: Mapping[str, Any]) -> dict[str, Any]:
        """Return JSON, retrying only transient failures and caching successful responses."""
        clean_params = {key: value for key, value in params.items() if value is not None}
        key = self._cache_key(path, clean_params)
        cached = await self._cached(key)
        if cached is not None:
            return cached

        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.get(url, params=clean_params)
                if response.status_code in self.RETRYABLE_STATUS_CODES:
                    retry_after = response.headers.get("Retry-After")
                    delay = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 0.25 * 2**attempt
                    )
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(delay, 4.0))
                        continue
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise UpstreamAPIError(f"{self.provider} returned an unexpected response shape")
                await self._store(key, payload)
                return payload
            except (httpx.HTTPError, ValueError, UpstreamAPIError) as exc:
                last_error = exc
                if attempt < self.max_retries and isinstance(
                    exc, (httpx.TimeoutException, httpx.NetworkError)
                ):
                    await asyncio.sleep(0.25 * 2**attempt)
                    continue
                break

        message = f"{self.provider} request failed"
        if isinstance(last_error, httpx.HTTPStatusError):
            status = last_error.response.status_code
            if status == 401 or status == 403:
                message += ": authentication was rejected; check the API key"
            elif status == 429:
                message += ": rate limit exceeded; try again later"
            else:
                message += f" with HTTP {status}"
        elif last_error is not None:
            message += f": {last_error}"
        raise UpstreamAPIError(message) from last_error
