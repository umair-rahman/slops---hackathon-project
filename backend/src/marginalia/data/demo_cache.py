"""
Live Fire Demo Mode — Pre-cached venue data for reliable demos.

Provides instant demo data when OpenReview is slow or unavailable.
Also used for the hackathon demo to ensure reliable live presentation.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Pre-cached demo data directory
DEMO_DIR = Path(__file__).parent.parent.parent.parent.parent / "eval" / "demo_cache"


# Synthetic demo data that mimics real OpenReview structure
# Used when live data is unavailable
DEMO_VENUES: dict[str, dict] = {
    "ICLR.cc/2024/Conference": {
        "venue_id": "ICLR.cc/2024/Conference",
        "total_papers": 7262,
        "total_reviews": 21786,
        "flagged_count": 2614,
        "flagged_percent": 12.0,
        "collusion_count": 47,
        "avg_score": 38.2,
        "score_distribution": [1200, 1800, 2400, 3100, 2800, 2600, 2400, 2100, 1900, 1486],
        "top_suspect_reviewers": [
            {
                "reviewer_id": "~Anonymous_Reviewer_8392",
                "total_reviews": 8,
                "avg_ghost_score": 91.2,
                "has_dna_cluster": True,
                "drift_detected": True,
            },
            {
                "reviewer_id": "~Anonymous_Reviewer_4471",
                "total_reviews": 6,
                "avg_ghost_score": 88.7,
                "has_dna_cluster": True,
                "drift_detected": False,
            },
            {
                "reviewer_id": "~Anonymous_Reviewer_2156",
                "total_reviews": 7,
                "avg_ghost_score": 85.3,
                "has_dna_cluster": True,
                "drift_detected": True,
            },
            {
                "reviewer_id": "~Anonymous_Reviewer_9034",
                "total_reviews": 5,
                "avg_ghost_score": 82.1,
                "has_dna_cluster": False,
                "drift_detected": False,
            },
            {
                "reviewer_id": "~Anonymous_Reviewer_6712",
                "total_reviews": 9,
                "avg_ghost_score": 79.8,
                "has_dna_cluster": True,
                "drift_detected": True,
            },
        ],
        "message": "Demo data — pre-cached for reliable presentation",
    },
    "NeurIPS.cc/2024/Conference": {
        "venue_id": "NeurIPS.cc/2024/Conference",
        "total_papers": 15671,
        "total_reviews": 47013,
        "flagged_count": 5641,
        "flagged_percent": 12.0,
        "collusion_count": 103,
        "avg_score": 37.8,
        "score_distribution": [2600, 3900, 5200, 6700, 6100, 5600, 5200, 4500, 4100, 3113],
        "top_suspect_reviewers": [
            {
                "reviewer_id": "~Anonymous_Reviewer_1847",
                "total_reviews": 10,
                "avg_ghost_score": 93.4,
                "has_dna_cluster": True,
                "drift_detected": True,
            },
            {
                "reviewer_id": "~Anonymous_Reviewer_5523",
                "total_reviews": 8,
                "avg_ghost_score": 89.1,
                "has_dna_cluster": True,
                "drift_detected": False,
            },
        ],
        "message": "Demo data — pre-cached for reliable presentation",
    },
    "ICML.cc/2024/Conference": {
        "venue_id": "ICML.cc/2024/Conference",
        "total_papers": 9473,
        "total_reviews": 28419,
        "flagged_count": 3410,
        "flagged_percent": 12.0,
        "collusion_count": 62,
        "avg_score": 38.5,
        "score_distribution": [1560, 2340, 3120, 4040, 3680, 3360, 3120, 2700, 2460, 2039],
        "top_suspect_reviewers": [
            {
                "reviewer_id": "~Anonymous_Reviewer_3391",
                "total_reviews": 7,
                "avg_ghost_score": 90.6,
                "has_dna_cluster": True,
                "drift_detected": True,
            },
        ],
        "message": "Demo data — pre-cached for reliable presentation",
    },
}


def get_demo_venue(venue_id: str) -> dict | None:
    """Get pre-cached demo data for a venue."""
    return DEMO_VENUES.get(venue_id)


def is_demo_venue(venue_id: str) -> bool:
    """Check if a venue has pre-cached demo data."""
    return venue_id in DEMO_VENUES


def list_demo_venues() -> list[str]:
    """List all available demo venues."""
    return list(DEMO_VENUES.keys())
