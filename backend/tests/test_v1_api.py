"""Tests for Public API v1 endpoints."""

import time

from fastapi.testclient import TestClient

from marginalia.main import app

client = TestClient(app)

NOW_MS = int(time.time() * 1000)
HOUR_MS = 3600 * 1000
MINUTE_MS = 60 * 1000


class TestV1Health:
    def test_v1_health_returns_ok(self):
        r = client.get("/api/v1/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["version"] == "1.0.0"
        assert len(data["endpoints"]) >= 3


class TestV1Analyze:
    AI_REVIEW = (
        "This paper presents an interesting contribution to the field. "
        "The methodology is well-described and the results are promising. "
        "The authors have done a good job. I recommend acceptance."
    )
    HUMAN_REVIEW = (
        "Equation 5 in Section 3.2 has a sign error. Figure 4(b) is unclear. "
        "Table 2 is missing confidence intervals. Algorithm 1 on page 8 has a bug."
    )

    def test_v1_analyze_ai_review(self):
        r = client.post("/api/v1/analyze", json={"review_text": self.AI_REVIEW})
        assert r.status_code == 200
        data = r.json()
        assert data["overall"] > 50
        assert "label" in data
        assert "explanation" in data

    def test_v1_analyze_human_review(self):
        r = client.post("/api/v1/analyze", json={"review_text": self.HUMAN_REVIEW})
        assert r.status_code == 200
        data = r.json()
        assert data["overall"] < 50

    def test_v1_analyze_rejects_short_review(self):
        r = client.post("/api/v1/analyze", json={"review_text": "short"})
        assert r.status_code == 422

    def test_v1_analyze_rejects_too_long_review(self):
        r = client.post("/api/v1/analyze", json={"review_text": "x" * 10001})
        assert r.status_code == 422

    def test_v1_analyze_with_arxiv_id(self):
        r = client.post(
            "/api/v1/analyze",
            json={"review_text": self.AI_REVIEW, "paper_arxiv_id": "1706.03762"},
        )
        # Should succeed (paper fetch may fail gracefully)
        assert r.status_code in (200, 500)


class TestV1Collusion:
    TEMPLATE = (
        "This paper presents {} contribution. The proposed method shows {} results. "
        "However, the experimental setup lacks detail. "
        "Overall, this is a solid paper. I recommend acceptance with minor revisions."
    )

    def test_detects_collusion(self):
        reviews = [
            {"reviewer_id": "A", "review_text": self.TEMPLATE.format("an interesting", "promising")},
            {"reviewer_id": "B", "review_text": self.TEMPLATE.format("a novel", "competitive")},
            {"reviewer_id": "C", "review_text": self.TEMPLATE.format("a new", "strong")},
        ]
        r = client.post(
            "/api/v1/collusion",
            json={"paper_id": "paper_001", "reviews": reviews},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["paper_id"] == "paper_001"
        assert data["total_reviewers"] == 3
        assert "collusion_detected" in data
        assert "collusion_score" in data
        assert 0 <= data["collusion_score"] <= 100

    def test_collusion_rejects_single_review(self):
        r = client.post(
            "/api/v1/collusion",
            json={
                "paper_id": "p",
                "reviews": [{"reviewer_id": "A", "review_text": "Some review text here."}],
            },
        )
        assert r.status_code == 422

    def test_collusion_flagged_pairs_structure(self):
        reviews = [
            {"reviewer_id": "A", "review_text": self.TEMPLATE.format("an interesting", "promising")},
            {"reviewer_id": "B", "review_text": self.TEMPLATE.format("a novel", "competitive")},
        ]
        r = client.post(
            "/api/v1/collusion",
            json={"paper_id": "p", "reviews": reviews},
        )
        assert r.status_code == 200
        data = r.json()
        for pair in data["flagged_pairs"]:
            assert "reviewer_a" in pair
            assert "reviewer_b" in pair
            assert "similarity" in pair
            assert 0 <= pair["similarity"] <= 1


class TestV1TimeOnTask:
    def test_plausible_timing(self):
        reviews = [
            {"review_id": "r1", "review_text": " ".join(["word"] * 300), "timestamp_ms": NOW_MS},
            {"review_id": "r2", "review_text": " ".join(["word"] * 300), "timestamp_ms": NOW_MS + 2 * HOUR_MS},
        ]
        r = client.post(
            "/api/v1/time-on-task",
            json={"reviewer_id": "reviewer_1", "reviews": reviews},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["reviewer_id"] == "reviewer_1"
        assert not data["burst_detected"]
        assert data["time_on_task_score"] < 50

    def test_burst_timing(self):
        reviews = [
            {"review_id": f"r{i}", "review_text": " ".join(["word"] * 300),
             "timestamp_ms": NOW_MS + i * 30 * 1000}  # 30 seconds apart
            for i in range(4)
        ]
        r = client.post(
            "/api/v1/time-on-task",
            json={"reviewer_id": "reviewer_burst", "reviews": reviews},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["burst_detected"]
        assert data["time_on_task_score"] > 0

    def test_empty_reviews_rejected(self):
        r = client.post(
            "/api/v1/time-on-task",
            json={"reviewer_id": "r", "reviews": []},
        )
        assert r.status_code == 422

    def test_response_structure(self):
        reviews = [
            {"review_id": "r1", "review_text": "Some review text here.", "timestamp_ms": NOW_MS},
        ]
        r = client.post(
            "/api/v1/time-on-task",
            json={"reviewer_id": "reviewer_1", "reviews": reviews},
        )
        assert r.status_code == 200
        data = r.json()
        required_fields = [
            "reviewer_id", "total_reviews", "implausible_count",
            "burst_detected", "time_on_task_score", "implausible_reviews"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
