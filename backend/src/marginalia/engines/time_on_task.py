"""
Time-on-Task Estimation.

Detects implausible review submission patterns:
- Too many long reviews submitted in too short a time window
- Minimum reading time violated (can't read 10-page paper in 30 seconds)
- Burst submission patterns (all reviews submitted within minutes)

These are secondary signals — not definitive proof of AI use, but strong
indicators when combined with other signals.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Empirical constants
WORDS_PER_MINUTE_READING = 250       # average academic reading speed
WORDS_PER_MINUTE_WRITING = 30        # average careful writing speed
MIN_PAPER_PAGES = 8                  # minimum pages for a typical ML paper
WORDS_PER_PAGE = 350                 # approximate words per page
MIN_PAPER_WORDS = MIN_PAPER_PAGES * WORDS_PER_PAGE  # ~2800 words

# Minimum realistic time to read + write a review (seconds)
# Read 2800 words + write 300 words
MIN_REALISTIC_SECONDS = (
    (MIN_PAPER_WORDS / WORDS_PER_MINUTE_READING) * 60
    + (300 / WORDS_PER_MINUTE_WRITING) * 60
)  # ~1200 seconds = 20 minutes


@dataclass
class ReviewTiming:
    review_id: str
    reviewer_id: str
    review_word_count: int
    timestamp_ms: int
    min_realistic_seconds: float
    implausible: bool
    reason: str | None = None


@dataclass
class TimeOnTaskResult:
    reviewer_id: str
    total_reviews: int
    implausible_count: int
    burst_detected: bool
    burst_window_seconds: float | None
    reviews_in_burst: int
    implausible_reviews: list[ReviewTiming]
    time_on_task_score: float  # 0-100, higher = more suspicious


def estimate_time_on_task(
    reviewer_id: str,
    reviews: list[tuple[str, str, int]],  # (review_id, review_text, timestamp_ms)
    paper_word_counts: dict[str, int] | None = None,
) -> TimeOnTaskResult:
    """
    Estimate whether a reviewer's submission timing is plausible.

    Args:
        reviewer_id: The reviewer being analyzed.
        reviews: List of (review_id, review_text, timestamp_ms).
        paper_word_counts: Optional dict of review_id → paper word count.
                          If not provided, uses MIN_PAPER_WORDS as default.

    Returns:
        TimeOnTaskResult with implausibility flags.
    """
    if not reviews:
        return TimeOnTaskResult(
            reviewer_id=reviewer_id,
            total_reviews=0,
            implausible_count=0,
            burst_detected=False,
            burst_window_seconds=None,
            reviews_in_burst=0,
            implausible_reviews=[],
            time_on_task_score=0.0,
        )

    # Sort by timestamp
    sorted_reviews = sorted(reviews, key=lambda r: r[2])

    review_timings: list[ReviewTiming] = []

    for review_id, review_text, timestamp_ms in sorted_reviews:
        review_words = len(review_text.split())
        paper_words = (paper_word_counts or {}).get(review_id, MIN_PAPER_WORDS)

        # Minimum time: read paper + write review
        min_read_secs = (paper_words / WORDS_PER_MINUTE_READING) * 60
        min_write_secs = (review_words / WORDS_PER_MINUTE_WRITING) * 60
        min_total_secs = min_read_secs + min_write_secs

        review_timings.append(
            ReviewTiming(
                review_id=review_id,
                reviewer_id=reviewer_id,
                review_word_count=review_words,
                timestamp_ms=timestamp_ms,
                min_realistic_seconds=round(min_total_secs, 1),
                implausible=False,
            )
        )

    # Detect burst: multiple reviews submitted within a short window
    burst_detected = False
    burst_window_seconds: float | None = None
    reviews_in_burst = 0

    if len(sorted_reviews) >= 2:
        timestamps = [r[2] for r in sorted_reviews]
        # Check all consecutive windows
        for window_size in range(2, len(timestamps) + 1):
            for start in range(len(timestamps) - window_size + 1):
                window_ts = timestamps[start:start + window_size]
                window_secs = (window_ts[-1] - window_ts[0]) / 1000.0

                # Total minimum time for all reviews in window
                total_min_secs = sum(
                    rt.min_realistic_seconds
                    for rt in review_timings[start:start + window_size]
                )

                if window_secs < total_min_secs * 0.3 and window_size >= 2:
                    # Submitted in less than 30% of minimum realistic time
                    burst_detected = True
                    burst_window_seconds = round(window_secs, 1)
                    reviews_in_burst = max(reviews_in_burst, window_size)

                    # Mark all reviews in this burst as implausible
                    for rt in review_timings[start:start + window_size]:
                        if not rt.implausible:
                            rt.implausible = True
                            rt.reason = (
                                f"Part of burst: {window_size} reviews in "
                                f"{window_secs:.0f}s (min realistic: {total_min_secs:.0f}s)"
                            )

    implausible_reviews = [rt for rt in review_timings if rt.implausible]
    implausible_count = len(implausible_reviews)

    # Time-on-task score: 0-100 (higher = more suspicious)
    if implausible_count == 0 and not burst_detected:
        score = 0.0
    else:
        burst_factor = 1.0 if burst_detected else 0.0
        implausible_ratio = implausible_count / max(len(review_timings), 1)
        score = round(min(100.0, (burst_factor * 50 + implausible_ratio * 50)), 1)

    return TimeOnTaskResult(
        reviewer_id=reviewer_id,
        total_reviews=len(reviews),
        implausible_count=implausible_count,
        burst_detected=burst_detected,
        burst_window_seconds=burst_window_seconds,
        reviews_in_burst=reviews_in_burst,
        implausible_reviews=implausible_reviews,
        time_on_task_score=score,
    )
