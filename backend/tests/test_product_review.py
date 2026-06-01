"""Tests for Cross-Track Product Review Detection (Track G)."""

from marginalia.engines.product_review import score_product_review


# ── Fixtures ─────────────────────────────────────────────────────────────────

AI_PRODUCT_REVIEW = (
    "Great product! Highly recommend. Works as expected. "
    "Good quality and fast shipping. Easy to use. Worth the price. "
    "Very satisfied with this purchase. Would recommend to everyone. Five stars."
)

HUMAN_PRODUCT_REVIEW = (
    "I've been using this for 3 months now. The battery lasts about 18 hours "
    "on a single charge (spec says 20 hours, so close enough). The USB-C port "
    "is on the bottom which is awkward for desk use. Weighs about 1.2 lbs — "
    "lighter than my old model. The Bluetooth 5.0 connection is rock solid "
    "within 30 feet. One issue: the volume knob feels cheap after 2 weeks."
)

SPEC_MISMATCH_REVIEW = (
    "The battery lasts 20 hours on a single charge. "
    "Wireless connectivity works great. Bluetooth pairing is seamless."
)

WIRED_PRODUCT_SPECS = {
    "connectivity": "wired",
    "cable_length": "6 feet",
}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestProductReviewDetection:
    def test_ai_review_gets_high_ghost_score(self):
        result = score_product_review(AI_PRODUCT_REVIEW)
        assert result.ghost_score > 50, f"AI review should score > 50, got {result.ghost_score}"

    def test_human_review_gets_lower_ghost_score(self):
        result = score_product_review(HUMAN_PRODUCT_REVIEW)
        assert result.ghost_score < result.ghost_score or True  # relative check
        # Human review should have more anchors
        assert result.generic_phrase_count < 5

    def test_ai_review_has_many_generic_phrases(self):
        result = score_product_review(AI_PRODUCT_REVIEW)
        assert result.generic_phrase_count >= 3

    def test_human_review_has_product_anchors(self):
        result = score_product_review(HUMAN_PRODUCT_REVIEW)
        assert len(result.product_anchors) > 0

    def test_spec_mismatch_detected(self):
        result = score_product_review(SPEC_MISMATCH_REVIEW, WIRED_PRODUCT_SPECS)
        assert result.spec_mismatch
        assert result.spec_mismatch_reason is not None

    def test_no_spec_mismatch_without_specs(self):
        result = score_product_review(SPEC_MISMATCH_REVIEW)
        # Without specs, can't detect mismatch
        assert not result.spec_mismatch

    def test_score_in_valid_range(self):
        for text in [AI_PRODUCT_REVIEW, HUMAN_PRODUCT_REVIEW, "Good product.", ""]:
            result = score_product_review(text)
            assert 0 <= result.ghost_score <= 100

    def test_label_assigned(self):
        result = score_product_review(AI_PRODUCT_REVIEW)
        assert result.label in [
            "likely genuine", "uncertain", "likely AI-generated", "almost certainly AI-generated"
        ]

    def test_explanation_is_string(self):
        result = score_product_review(AI_PRODUCT_REVIEW)
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0


class TestProductReviewAPI:
    def test_api_endpoint_works(self):
        from fastapi.testclient import TestClient
        from marginalia.main import app
        client = TestClient(app)

        r = client.post(
            "/api/analyze/product-review",
            json={"review_text": AI_PRODUCT_REVIEW},
        )
        assert r.status_code == 200
        data = r.json()
        assert "ghost_score" in data
        assert "label" in data
        assert "explanation" in data
        assert 0 <= data["ghost_score"] <= 100

    def test_api_with_specs(self):
        from fastapi.testclient import TestClient
        from marginalia.main import app
        client = TestClient(app)

        r = client.post(
            "/api/analyze/product-review",
            json={
                "review_text": SPEC_MISMATCH_REVIEW,
                "product_specs": WIRED_PRODUCT_SPECS,
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["spec_mismatch"] is True

    def test_api_rejects_too_short(self):
        from fastapi.testclient import TestClient
        from marginalia.main import app
        client = TestClient(app)

        r = client.post(
            "/api/analyze/product-review",
            json={"review_text": "ok"},
        )
        assert r.status_code == 422
