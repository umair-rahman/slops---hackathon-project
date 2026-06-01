"""Tests for Time-on-Task Estimation."""

import time

from marginalia.engines.time_on_task import estimate_time_on_task


# ── Fixtures ─────────────────────────────────────────────────────────────────

LONG_REVIEW = " ".join(["word"] * 400)  # 400-word review
SHORT_REVIEW = " ".join(["word"] * 50)  # 50-word review

NOW_MS = int(time.time() * 1000)
HOUR_MS = 3600 * 1000
MINUTE_MS = 60 * 1000


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestTimeOnTask:
    def test_empty_reviews(self):
        result = estimate_time_on_task("reviewer_1", [])
        assert result.total_reviews == 0
        assert result.time_on_task_score == 0.0

    def test_single_review_no_burst(self):
        reviews = [("r1", LONG_REVIEW, NOW_MS)]
        result = estimate_time_on_task("reviewer_1", reviews)
        assert not result.burst_detected
        assert result.implausible_count == 0

    def test_plausible_timing(self):
        # Reviews submitted 2 hours apart — plausible
        reviews = [
            ("r1", LONG_REVIEW, NOW_MS),
            ("r2", LONG_REVIEW, NOW_MS + 2 * HOUR_MS),
            ("r3", LONG_REVIEW, NOW_MS + 4 * HOUR_MS),
        ]
        result = estimate_time_on_task("reviewer_1", reviews)
        assert not result.burst_detected
        assert result.time_on_task_score < 50

    def test_burst_detection(self):
        # 3 long reviews submitted within 5 minutes — implausible
        reviews = [
            ("r1", LONG_REVIEW, NOW_MS),
            ("r2", LONG_REVIEW, NOW_MS + 2 * MINUTE_MS),
            ("r3", LONG_REVIEW, NOW_MS + 4 * MINUTE_MS),
        ]
        result = estimate_time_on_task("reviewer_1", reviews)
        assert result.burst_detected
        assert result.implausible_count > 0
        assert result.time_on_task_score > 0

    def test_burst_score_is_high(self):
        # Extreme burst: 5 reviews in 30 seconds
        reviews = [
            (f"r{i}", LONG_REVIEW, NOW_MS + i * 6000)  # 6 seconds apart
            for i in range(5)
        ]
        result = estimate_time_on_task("reviewer_1", reviews)
        assert result.burst_detected
        assert result.time_on_task_score > 30

    def test_score_in_valid_range(self):
        reviews = [
            ("r1", LONG_REVIEW, NOW_MS),
            ("r2", LONG_REVIEW, NOW_MS + 30 * 1000),  # 30 seconds apart
        ]
        result = estimate_time_on_task("reviewer_1", reviews)
        assert 0 <= result.time_on_task_score <= 100

    def test_reviewer_id_preserved(self):
        reviews = [("r1", SHORT_REVIEW, NOW_MS)]
        result = estimate_time_on_task("test_reviewer", reviews)
        assert result.reviewer_id == "test_reviewer"

    def test_implausible_reviews_have_reasons(self):
        reviews = [
            ("r1", LONG_REVIEW, NOW_MS),
            ("r2", LONG_REVIEW, NOW_MS + 10 * 1000),  # 10 seconds
        ]
        result = estimate_time_on_task("reviewer_1", reviews)
        if result.implausible_reviews:
            for rt in result.implausible_reviews:
                assert rt.reason is not None
                assert len(rt.reason) > 0
