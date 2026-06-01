"""End-to-end API tests using FastAPI TestClient."""

from fastapi.testclient import TestClient

from marginalia.main import app

client = TestClient(app)


# ── Health Endpoint ─────────────────────────────────────────────────────────

def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "marginalia"


def test_root_returns_message():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "marginalia" in data["message"].lower()


# ── Single Review Analysis ──────────────────────────────────────────────────

class TestAnalyzeReviewEndpoint:
    AI_REVIEW = (
        "This paper presents an interesting contribution to the field of machine learning. "
        "The methodology is well-described and the results are promising. "
        "The authors have done a good job of explaining their approach. "
        "The writing is clear and the paper is well-organized. "
        "I recommend acceptance with minor revisions."
    )

    HUMAN_REVIEW = (
        "The paper proposes a novel attention mechanism described in Section 3.2. "
        "However, Equation 5 contains a derivation error. Figure 4(b) shows the ablation. "
        "Table 2 is missing confidence intervals. In Section 5.1, accuracy claims contradict Figure 6. "
        "Algorithm 1 on page 8 has an off-by-one error in the loop bounds."
    )

    def test_analyze_ai_review_returns_high_score(self):
        response = client.post(
            "/api/analyze/review",
            json={"review_text": self.AI_REVIEW},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall"] > 50
        assert data["specificity"]["score"] < 50
        assert isinstance(data["explanation"], str)
        assert "label" in data
        assert data["confidence_low"] <= data["overall"] <= data["confidence_high"]

    def test_analyze_human_review_returns_low_score(self):
        response = client.post(
            "/api/analyze/review",
            json={"review_text": self.HUMAN_REVIEW},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["overall"] < 50
        assert data["specificity"]["score"] > 50
        assert data["specificity"]["total_anchors"] >= 4

    def test_analyze_returns_sentence_breakdown(self):
        response = client.post(
            "/api/analyze/review",
            json={"review_text": self.HUMAN_REVIEW},
        )
        data = response.json()
        sentences = data["specificity"]["sentences"]
        assert len(sentences) > 0
        for s in sentences:
            assert "text" in s
            assert "anchor_count" in s
            assert isinstance(s["is_hallucinated"], bool)

    def test_analyze_rejects_too_short_review(self):
        response = client.post(
            "/api/analyze/review",
            json={"review_text": "short"},
        )
        # Pydantic validation should reject (min_length=20)
        assert response.status_code == 422

    def test_analyze_handles_no_paper_id(self):
        response = client.post(
            "/api/analyze/review",
            json={"review_text": self.HUMAN_REVIEW},
        )
        assert response.status_code == 200
        data = response.json()
        # Asymmetry score should be 0 when no paper provided
        assert data["asymmetry"]["score"] == 0.0
        assert data["batch_dna"]["available"] is False


# ── Batch Analysis ──────────────────────────────────────────────────────────

class TestBatchAnalyze:
    def test_batch_clusters_ai_reviews(self):
        ai_template = (
            "This paper presents {} contribution to the field. "
            "The proposed method shows {} results. "
            "However, the methodology section could be clearer. "
            "Additionally, the experimental setup lacks detail. "
            "Overall, this is a solid paper. I recommend acceptance with minor revisions."
        )

        reviews = [
            {"review_id": "r1", "review_text": ai_template.format("an interesting", "promising")},
            {"review_id": "r2", "review_text": ai_template.format("a novel", "competitive")},
            {"review_id": "r3", "review_text": ai_template.format("a new", "strong")},
        ]

        response = client.post(
            "/api/analyze/batch",
            json={"reviews": reviews},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        # At least one review should be flagged as part of a cluster
        has_cluster = any(r["batch_dna"]["cluster_size"] and r["batch_dna"]["cluster_size"] >= 2 for r in data)
        assert has_cluster, "AI batch should produce a cluster"

    def test_batch_rejects_empty(self):
        response = client.post(
            "/api/analyze/batch",
            json={"reviews": []},
        )
        assert response.status_code == 400


# ── Conference Scan SSE ─────────────────────────────────────────────────────

class TestConferenceScan:
    def test_scan_endpoint_responds(self):
        # Use a fake venue — backend should gracefully return empty
        response = client.get("/api/scan/conference?venue_id=NONEXISTENT/Venue&max_papers=1")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("text/event-stream")

    def test_scan_streams_events(self):
        with client.stream("GET", "/api/scan/conference?venue_id=NONEXISTENT/Venue&max_papers=1") as response:
            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    events.append(line)
                if len(events) >= 1:
                    break
            assert len(events) >= 1
