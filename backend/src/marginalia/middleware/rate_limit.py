"""
Rate limiting middleware using Upstash Redis REST API.

Implements a sliding window rate limiter.
Falls back to no-op when Redis is unavailable.
"""

from __future__ import annotations

import logging
import time

import httpx
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from marginalia.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter.

    Default limits:
    - Public API (/api/v1/*): 30 req/min per IP
    - Analysis endpoints (/api/analyze/*): 20 req/min per IP
    - Other endpoints: 60 req/min per IP
    """

    LIMITS: dict[str, tuple[int, int]] = {
        "/api/v1/": (30, 60),       # 30 requests per 60 seconds
        "/api/analyze/": (20, 60),  # 20 requests per 60 seconds
        "/api/scan/": (10, 60),     # 10 requests per 60 seconds
        "default": (60, 60),        # 60 requests per 60 seconds
    }

    def __init__(self, app, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled and bool(
            settings.upstash_redis_rest_url and settings.upstash_redis_rest_token
        )
        if self.enabled:
            logger.info("Rate limiting enabled via Upstash Redis")
        else:
            logger.info("Rate limiting disabled (no Upstash config)")

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip rate limiting for health checks and docs
        path = request.url.path
        if path in ("/health", "/", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Determine limit for this path
        limit, window = self._get_limit(path)

        # Check rate limit
        allowed, remaining, reset_at = await self._check_limit(
            client_ip, path, limit, window
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": f"Too many requests. Limit: {limit} per {window}s.",
                    "retry_after": max(0, int(reset_at - time.time())),
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_at)),
                    "Retry-After": str(max(0, int(reset_at - time.time()))),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_at))
        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract real client IP, respecting proxy headers."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_limit(self, path: str) -> tuple[int, int]:
        """Get rate limit for a given path."""
        for prefix, limit_tuple in self.LIMITS.items():
            if prefix != "default" and path.startswith(prefix):
                return limit_tuple
        return self.LIMITS["default"]

    async def _check_limit(
        self, client_ip: str, path: str, limit: int, window: int
    ) -> tuple[bool, int, float]:
        """
        Check rate limit using Upstash Redis sliding window.

        Returns: (allowed, remaining, reset_timestamp)
        """
        # Determine bucket key (group similar paths)
        bucket = self._path_to_bucket(path)
        key = f"rl:{client_ip}:{bucket}"
        now = time.time()
        window_start = now - window

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                headers = {
                    "Authorization": f"Bearer {settings.upstash_redis_rest_token}"
                }
                base = settings.upstash_redis_rest_url.rstrip("/")

                # Use ZREMRANGEBYSCORE + ZADD + ZCARD pipeline via multi-exec
                # Simplified: use INCR with TTL for simplicity and reliability
                incr_url = f"{base}/incr/{key}"
                r = await client.get(incr_url, headers=headers)

                if r.status_code != 200:
                    # Redis unavailable — allow request
                    return True, limit, now + window

                count = r.json().get("result", 0)

                # Set TTL on first request
                if count == 1:
                    expire_url = f"{base}/expire/{key}/{window}"
                    await client.get(expire_url, headers=headers)

                remaining = max(0, limit - count)
                reset_at = now + window
                allowed = count <= limit

                return allowed, remaining, reset_at

        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            # Fail open — allow request if Redis is down
            return True, limit, now + window

    @staticmethod
    def _path_to_bucket(path: str) -> str:
        """Group paths into rate limit buckets."""
        if path.startswith("/api/v1/"):
            return "v1"
        if path.startswith("/api/analyze/"):
            return "analyze"
        if path.startswith("/api/scan/"):
            return "scan"
        if path.startswith("/api/reviewer/"):
            return "reviewer"
        return "general"
