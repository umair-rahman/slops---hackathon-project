"""
Upstash Redis cache layer using REST API.

Avoids the redis-py protocol dependency and works over HTTPS.
Falls back to an in-memory cache when Upstash isn't configured.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from marginalia.config import settings

logger = logging.getLogger(__name__)


class CacheBackend:
    """Async cache interface — Upstash REST or in-memory."""

    async def get(self, key: str) -> Any | None:
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        raise NotImplementedError

    async def delete(self, key: str) -> None:
        raise NotImplementedError


class InMemoryCache(CacheBackend):
    """Fallback in-memory cache with TTL."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at < time.time():
                self._store.pop(key, None)
                return None
            return value

    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        async with self._lock:
            self._store[key] = (time.time() + ttl_seconds, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


class UpstashRedisCache(CacheBackend):
    """Upstash Redis via REST API — works without redis-py."""

    def __init__(self, url: str, token: str) -> None:
        self.url = url.rstrip("/")
        self.token = token
        self._client = httpx.AsyncClient(
            timeout=10.0,
            headers={"Authorization": f"Bearer {token}"},
        )

    async def get(self, key: str) -> Any | None:
        try:
            r = await self._client.get(f"{self.url}/get/{key}")
            if r.status_code != 200:
                return None
            data = r.json()
            raw = data.get("result")
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        except Exception as e:
            logger.warning(f"Cache GET failed for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 86400) -> None:
        try:
            payload = json.dumps(value) if not isinstance(value, str) else value
            r = await self._client.post(
                f"{self.url}/set/{key}",
                params={"EX": ttl_seconds},
                content=payload,
                headers={"Content-Type": "application/json"},
            )
            if r.status_code != 200:
                logger.warning(f"Cache SET failed for {key}: {r.status_code}")
        except Exception as e:
            logger.warning(f"Cache SET failed for {key}: {e}")

    async def delete(self, key: str) -> None:
        try:
            await self._client.get(f"{self.url}/del/{key}")
        except Exception as e:
            logger.warning(f"Cache DEL failed for {key}: {e}")

    async def close(self) -> None:
        await self._client.aclose()


def get_cache() -> CacheBackend:
    """Get configured cache backend (Upstash if configured, else in-memory)."""
    url = settings.upstash_redis_rest_url
    token = settings.upstash_redis_rest_token
    if url and token:
        logger.info("Using Upstash Redis cache")
        return UpstashRedisCache(url, token)
    logger.info("Using in-memory cache")
    return InMemoryCache()


# Module-level singleton
cache: CacheBackend = get_cache()
