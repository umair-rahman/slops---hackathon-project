"""Conference / venue scan endpoint with SSE streaming."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from marginalia.data.demo_cache import get_demo_venue, is_demo_venue
from marginalia.data.openreview import openreview_client
from marginalia.engines.batch_dna import score_batch_dna
from marginalia.engines.collusion import detect_collusion_batch
from marginalia.engines.specificity import score_specificity

logger = logging.getLogger(__name__)
router = APIRouter()


async def _scan_stream(venue_id: str, max_papers: int) -> AsyncGenerator[str, None]:
    """Stream scan progress events via SSE."""

    def event(data: dict) -> str:
        return f"data: {json.dumps(data)}\n\n"

    try:
        # Step 1: Connect
        yield event({"type": "progress", "message": f"Connecting to OpenReview: {venue_id}", "percent": 5})
        await asyncio.sleep(0.1)

        # Check for demo cache first (Live Fire mode)
        demo_data = get_demo_venue(venue_id)

        # Step 2: Fetch reviews
        yield event({"type": "progress", "message": "Fetching reviews from venue...", "percent": 15})
        reviews_data = await openreview_client.get_reviews(venue_id, max_papers)

        # If no live data, use demo cache
        if not reviews_data and demo_data:
            logger.info(f"Using demo cache for {venue_id}")
            yield event({"type": "progress", "message": "Using pre-cached demo data...", "percent": 95})
            await asyncio.sleep(0.2)
            yield event({"type": "complete", "data": demo_data})
            return

        if not reviews_data:
            yield event({
                "type": "complete",
                "data": {
                    "venue_id": venue_id,
                    "total_papers": 0,
                    "total_reviews": 0,
                    "flagged_count": 0,
                    "flagged_percent": 0.0,
                    "top_suspect_reviewers": [],
                    "score_distribution": [0] * 10,
                    "avg_score": 0.0,
                    "message": "No reviews found. Check venue ID or auth.",
                },
            })
            return

        yield event({
            "type": "progress",
            "message": f"Fetched {len(reviews_data)} reviews. Running specificity engine...",
            "percent": 40,
        })
        await asyncio.sleep(0.05)

        # Step 3: Specificity scoring (per-review)
        per_review_scores: dict[str, dict] = {}
        for r in reviews_data:
            spec = score_specificity(r.review_text)
            per_review_scores[r.review_id] = {
                "review_id": r.review_id,
                "reviewer_id": r.reviewer_id,
                "paper_id": r.paper_id,
                "spec_score": spec.score,
                "ghost_contribution": 100.0 - spec.score,
            }

        yield event({"type": "progress", "message": "Running batch DNA clustering per reviewer...", "percent": 70})
        await asyncio.sleep(0.05)

        # Step 4: Batch DNA per reviewer + Collusion per paper
        reviewer_groups: dict[str, list[tuple[str, str]]] = {}
        paper_groups: dict[str, list[tuple[str, str]]] = {}  # paper_id → [(reviewer_id, text)]
        for r in reviews_data:
            reviewer_groups.setdefault(r.reviewer_id, []).append((r.review_id, r.review_text))
            paper_groups.setdefault(r.paper_id, []).append((r.reviewer_id, r.review_text))

        all_dna_results: dict[str, "BatchDNAResult"] = {}  # type: ignore  # noqa: F821
        for reviewer_id, batch in reviewer_groups.items():
            if len(batch) >= 2:
                dna = score_batch_dna(batch)
                all_dna_results.update(dna)

        # Collusion detection across papers
        collusion_results = detect_collusion_batch(paper_groups)
        collusion_count = sum(1 for r in collusion_results.values() if r.collusion_detected)

        yield event({"type": "progress", "message": "Aggregating final ghost scores...", "percent": 90})
        await asyncio.sleep(0.05)

        # Step 5: Aggregate per-review final ghost score
        score_distribution = [0] * 10
        flagged = 0
        all_scores: list[float] = []

        for r in reviews_data:
            spec_data = per_review_scores[r.review_id]
            spec_ghost = spec_data["ghost_contribution"]

            dna = all_dna_results.get(r.review_id)
            if dna and dna.available and dna.score is not None:
                # Specificity (60%) + Batch DNA (40%) — no asymmetry without paper
                ghost = 0.6 * spec_ghost + 0.4 * dna.score
            else:
                ghost = spec_ghost

            ghost = max(0.0, min(100.0, ghost))
            all_scores.append(ghost)

            bucket = min(int(ghost / 10), 9)
            score_distribution[bucket] += 1

            if ghost >= 65:
                flagged += 1

        # Step 6: Top suspect reviewers
        reviewer_stats: dict[str, dict] = {}
        for i, r in enumerate(reviews_data):
            stats = reviewer_stats.setdefault(
                r.reviewer_id,
                {
                    "reviewer_id": r.reviewer_id,
                    "scores": [],
                    "has_dna_cluster": False,
                    "drift_detected": False,
                },
            )
            stats["scores"].append(all_scores[i])
            dna = all_dna_results.get(r.review_id)
            if dna and dna.cluster_size and dna.cluster_size >= 2:
                stats["has_dna_cluster"] = True

        top_reviewers = []
        for stats in reviewer_stats.values():
            scores_list = stats["scores"]
            avg = sum(scores_list) / len(scores_list) if scores_list else 0
            if avg >= 50 or stats["has_dna_cluster"]:
                top_reviewers.append({
                    "reviewer_id": stats["reviewer_id"],
                    "total_reviews": len(scores_list),
                    "avg_ghost_score": round(avg, 1),
                    "has_dna_cluster": stats["has_dna_cluster"],
                    "drift_detected": stats["drift_detected"],
                })

        top_reviewers.sort(key=lambda x: x["avg_ghost_score"], reverse=True)
        top_reviewers = top_reviewers[:20]

        unique_papers = len({r.paper_id for r in reviews_data})

        yield event({
            "type": "complete",
            "data": {
                "venue_id": venue_id,
                "total_papers": unique_papers,
                "total_reviews": len(reviews_data),
                "flagged_count": flagged,
                "flagged_percent": round(flagged / len(reviews_data) * 100, 1) if reviews_data else 0,
                "collusion_count": collusion_count,
                "top_suspect_reviewers": top_reviewers,
                "score_distribution": score_distribution,
                "avg_score": round(sum(all_scores) / len(all_scores), 1) if all_scores else 0,
            },
        })

    except Exception as e:
        logger.exception(f"Conference scan failed: {e}")
        yield event({"type": "error", "error": str(e)})


@router.get("/scan/conference")
async def scan_conference(venue_id: str, max_papers: int = 50) -> StreamingResponse:
    """
    Scan an entire OpenReview venue. Returns SSE stream.
    """
    return StreamingResponse(
        _scan_stream(venue_id, max_papers),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/scan/demo-venues")
async def list_demo_venues() -> dict:
    """List venues with pre-cached demo data for Live Fire mode."""
    from marginalia.data.demo_cache import list_demo_venues as _list
    return {"venues": _list()}
