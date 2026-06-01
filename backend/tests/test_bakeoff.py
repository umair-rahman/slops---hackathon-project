"""Tests for Bake-Off evaluation pipeline."""

import json
from pathlib import Path


class TestBakeoffDataset:
    """Verify the Bake-Off dataset is properly structured."""

    EVAL_DIR = Path(__file__).parent.parent.parent.parent / "marginalia" / "eval" / "dataset"

    def test_real_reviews_exist(self):
        real_dir = self.EVAL_DIR / "real_reviews"
        assert real_dir.exists(), f"Real reviews dir not found: {real_dir}"
        json_files = list(real_dir.glob("*.json"))
        assert len(json_files) >= 1

    def test_ai_reviews_exist(self):
        ai_dir = self.EVAL_DIR / "ai_reviews"
        assert ai_dir.exists(), f"AI reviews dir not found: {ai_dir}"
        json_files = list(ai_dir.glob("*.json"))
        assert len(json_files) >= 1

    def test_real_reviews_have_required_fields(self):
        real_dir = self.EVAL_DIR / "real_reviews"
        for f in real_dir.glob("*.json"):
            reviews = json.loads(f.read_text())
            for r in reviews:
                assert "id" in r, f"Missing 'id' in {f.name}"
                assert "label" in r, f"Missing 'label' in {f.name}"
                assert "text" in r, f"Missing 'text' in {f.name}"
                assert r["label"] == "human"
                assert len(r["text"]) >= 50

    def test_ai_reviews_have_required_fields(self):
        ai_dir = self.EVAL_DIR / "ai_reviews"
        for f in ai_dir.glob("*.json"):
            reviews = json.loads(f.read_text())
            for r in reviews:
                assert "id" in r
                assert "label" in r
                assert "text" in r
                assert r["label"] == "ai"
                assert len(r["text"]) >= 20

    def test_total_reviews_count(self):
        real_dir = self.EVAL_DIR / "real_reviews"
        ai_dir = self.EVAL_DIR / "ai_reviews"

        real_count = sum(
            len(json.loads(f.read_text()))
            for f in real_dir.glob("*.json")
        )
        ai_count = sum(
            len(json.loads(f.read_text()))
            for f in ai_dir.glob("*.json")
        )

        assert real_count >= 50, f"Need 50 real reviews, got {real_count}"
        assert ai_count >= 50, f"Need 50 AI reviews, got {ai_count}"

    def test_ai_reviews_have_diverse_prompts(self):
        ai_dir = self.EVAL_DIR / "ai_reviews"
        prompt_types = set()
        for f in ai_dir.glob("*.json"):
            reviews = json.loads(f.read_text())
            for r in reviews:
                if "prompt_type" in r:
                    prompt_types.add(r["prompt_type"])
        assert len(prompt_types) >= 4, f"Need 4+ prompt types, got {prompt_types}"


class TestBakeoffResults:
    """Verify Bake-Off results are saved and valid."""

    RESULTS_DIR = Path(__file__).parent.parent.parent.parent / "marginalia" / "eval" / "results"

    def test_metrics_json_exists(self):
        metrics_file = self.RESULTS_DIR / "metrics.json"
        assert metrics_file.exists(), "Run eval/run_bakeoff.py first"

    def test_metrics_have_required_fields(self):
        metrics_file = self.RESULTS_DIR / "metrics.json"
        if not metrics_file.exists():
            return  # Skip if not run yet

        data = json.loads(metrics_file.read_text())
        assert "metrics" in data
        assert "confusion_matrix" in data
        m = data["metrics"]
        assert "precision" in m
        assert "recall" in m
        assert "f1" in m
        assert "accuracy" in m

    def test_metrics_are_reasonable(self):
        metrics_file = self.RESULTS_DIR / "metrics.json"
        if not metrics_file.exists():
            return

        data = json.loads(metrics_file.read_text())
        m = data["metrics"]
        # Should be better than random (50%)
        assert m["accuracy"] > 0.5, f"Accuracy {m['accuracy']} should be > 50%"
        assert m["f1"] > 0.5, f"F1 {m['f1']} should be > 50%"
