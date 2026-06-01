"""
OpenReview API client with caching.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass

from marginalia.config import settings
from marginalia.data.cache import cache

logger = logging.getLogger(__name__)


@dataclass
class ReviewData:
    review_id: str
    paper_id: str
    paper_title: str
    reviewer_id: str
    review_text: str
    timestamp: int
    venue_id: str


class OpenReviewClient:
    """Async-friendly wrapper around openreview-py with cache."""

    def __init__(self) -> None:
        self._client = None
        self._initialized = False

    def _get_client(self):
        if self._initialized:
            return self._client

        try:
            from openreview.api import OpenReviewClient as ORClient

            kwargs: dict = {"baseurl": "https://api2.openreview.net"}
            if settings.openreview_username and settings.openreview_password:
                kwargs["username"] = settings.openreview_username
                kwargs["password"] = settings.openreview_password
            self._client = ORClient(**kwargs)
        except Exception as e:
            logger.warning(f"OpenReview client init failed: {e}")
            self._client = None

        self._initialized = True
        return self._client

    async def get_reviews(
        self,
        venue_id: str,
        max_papers: int = 100,
    ) -> list[ReviewData]:
        """Fetch reviews for a venue with caching. Returns empty list on error."""
        cache_key = f"openreview:reviews:{venue_id}:{max_papers}"

        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"OpenReview cache hit: {venue_id}")
            return [ReviewData(**r) for r in cached]

        loop = asyncio.get_event_loop()
        reviews = await loop.run_in_executor(
            None, self._fetch_reviews_sync, venue_id, max_papers
        )

        if reviews:
            await cache.set(
                cache_key,
                [asdict(r) for r in reviews],
                ttl_seconds=24 * 3600,  # 24 hours
            )
        return reviews

    def _fetch_reviews_sync(self, venue_id: str, max_papers: int) -> list[ReviewData]:
        client = self._get_client()
        if client is None:
            logger.warning("OpenReview client unavailable")
            return []

        reviews: list[ReviewData] = []

        try:
            submissions = client.get_all_notes(
                invitation=f"{venue_id}/-/Submission",
                details="replies",
                limit=max_papers,
            )
        except Exception as e:
            logger.error(f"OpenReview fetch error for {venue_id}: {e}")
            return []

        for submission in submissions[:max_papers]:
            paper_id = getattr(submission, "id", "")
            content = getattr(submission, "content", {}) or {}
            paper_title = (
                content.get("title", {}).get("value", "Unknown")
                if isinstance(content.get("title"), dict)
                else str(content.get("title", "Unknown"))
            )

            details = getattr(submission, "details", {}) or {}
            replies = details.get("replies", []) or []

            for reply in replies:
                invitations = reply.get("invitations", []) or [reply.get("invitation", "")]
                if not any("Official_Review" in inv for inv in invitations):
                    continue

                reply_content = reply.get("content", {}) or {}
                review_text = self._extract_review_text(reply_content)
                if not review_text:
                    continue

                signatures = reply.get("signatures", ["~Anonymous"])
                reviewer_id = signatures[0] if signatures else "~Anonymous"

                reviews.append(
                    ReviewData(
                        review_id=reply.get("id", ""),
                        paper_id=paper_id,
                        paper_title=paper_title,
                        reviewer_id=reviewer_id,
                        review_text=review_text,
                        timestamp=reply.get("cdate", 0),
                        venue_id=venue_id,
                    )
                )

        logger.info(f"Fetched {len(reviews)} reviews from {venue_id}")
        return reviews

    @staticmethod
    def _extract_review_text(content: dict) -> str:
        """Try multiple field names where review text might live."""
        for field in ["review", "comment", "main_review", "summary_of_the_paper"]:
            v = content.get(field)
            if isinstance(v, dict):
                value = v.get("value", "")
                if value and isinstance(value, str):
                    return value
            elif isinstance(v, str) and v:
                return v
        return ""

    async def get_reviewer_reviews(
        self,
        reviewer_id: str,
        venue_ids: list[str] | None = None,
    ) -> list[ReviewData]:
        """
        Fetch all reviews by a specific reviewer across venues.
        For Phase 4, uses cached venue data when available.
        """
        cache_key = f"openreview:reviewer:{reviewer_id}"
        cached = await cache.get(cache_key)
        if cached:
            return [ReviewData(**r) for r in cached]

        # Aggregate from cached venues
        all_reviews: list[ReviewData] = []
        venues = venue_ids or [
            "ICLR.cc/2024/Conference",
            "ICLR.cc/2025/Conference",
            "NeurIPS.cc/2024/Conference",
        ]
        for venue in venues:
            venue_reviews = await self.get_reviews(venue, max_papers=200)
            all_reviews.extend(r for r in venue_reviews if r.reviewer_id == reviewer_id)

        if all_reviews:
            await cache.set(
                cache_key,
                [asdict(r) for r in all_reviews],
                ttl_seconds=12 * 3600,
            )
        return all_reviews


openreview_client = OpenReviewClient()
