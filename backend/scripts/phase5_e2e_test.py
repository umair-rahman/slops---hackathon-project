"""Phase 5 end-to-end integration test."""

import json
import subprocess
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def test_1_bakeoff_results():
    section("[1] Bake-Off Results")
    results_file = Path(__file__).parent.parent.parent.parent / "marginalia" / "eval" / "results" / "metrics.json"
    assert results_file.exists(), f"Run eval/run_bakeoff.py first. File not found: {results_file}"
    data = json.loads(results_file.read_text())
    m = data["metrics"]
    print(f"  Precision:  {m['precision']:.1%}")
    print(f"  Recall:     {m['recall']:.1%}")
    print(f"  F1:         {m['f1']:.1%}")
    print(f"  Accuracy:   {m['accuracy']:.1%}")
    print(f"  FPR:        {m['false_positive_rate']:.1%}")
    assert m["f1"] > 0.5, f"F1 {m['f1']} should be > 50%"
    assert m["accuracy"] > 0.5
    print("  PASS")


def test_2_live_fire_demo_venues():
    section("[2] Live Fire — Demo Venues Endpoint")
    r = httpx.get(f"{BASE}/api/scan/demo-venues", timeout=5)
    assert r.status_code == 200
    data = r.json()
    venues = data["venues"]
    print(f"  Demo venues: {venues}")
    assert "ICLR.cc/2024/Conference" in venues
    assert "NeurIPS.cc/2024/Conference" in venues
    assert "ICML.cc/2024/Conference" in venues
    print("  PASS")


def test_3_live_fire_demo_scan():
    section("[3] Live Fire — Demo Scan (ICLR 2024)")
    with httpx.stream(
        "GET",
        f"{BASE}/api/scan/conference?venue_id=ICLR.cc/2024/Conference&max_papers=1",
        timeout=30,
    ) as r:
        assert r.status_code == 200
        events = []
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
            if any(e["type"] in ("complete", "error") for e in events):
                break

    complete_event = next((e for e in events if e["type"] == "complete"), None)
    assert complete_event is not None, "No complete event received"
    data = complete_event["data"]
    print(f"  venue: {data['venue_id']}")
    print(f"  total_reviews: {data['total_reviews']}")
    print(f"  flagged_percent: {data['flagged_percent']}%")
    # Demo data should have reviews
    assert data["total_reviews"] > 0
    print("  PASS")


def test_4_cross_track_product_review():
    section("[4] Cross-Track — Product Review Detection")
    ai_review = (
        "Great product! Highly recommend. Works as expected. "
        "Good quality and fast shipping. Easy to use. Worth the price. "
        "Very satisfied with this purchase. Would recommend to everyone."
    )
    r = httpx.post(
        f"{BASE}/api/analyze/product-review",
        json={"review_text": ai_review},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  ghost_score: {data['ghost_score']}")
    print(f"  label: {data['label']}")
    print(f"  generic_phrases: {data['generic_phrase_count']}")
    assert data["ghost_score"] > 50
    assert data["generic_phrase_count"] >= 3
    print("  PASS")


def test_5_spec_mismatch_detection():
    section("[5] Cross-Track — Spec Mismatch Detection")
    review = (
        "The battery lasts 20 hours on a single charge. "
        "Wireless connectivity works great. Bluetooth pairing is seamless."
    )
    r = httpx.post(
        f"{BASE}/api/analyze/product-review",
        json={
            "review_text": review,
            "product_specs": {"connectivity": "wired", "cable_length": "6 feet"},
        },
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  spec_mismatch: {data['spec_mismatch']}")
    print(f"  reason: {data['spec_mismatch_reason']}")
    assert data["spec_mismatch"] is True
    print("  PASS")


def test_6_cli_version():
    section("[6] CLI — version command")
    result = subprocess.run(
        [sys.executable, "-m", "marginalia.cli", "version"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert result.returncode == 0
    print(f"  output: {result.stdout.strip()}")
    assert "marginalia-ai" in result.stdout
    print("  PASS")


def test_7_cli_analyze():
    section("[7] CLI — analyze command")
    review = (
        "This paper presents an interesting contribution. "
        "The methodology is well-described. I recommend acceptance."
    )
    result = subprocess.run(
        [sys.executable, "-m", "marginalia.cli", "analyze", "--json", review],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        env={**__import__("os").environ, "PYTHONPATH": "src"},
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    print(f"  ghost score: {data['overall']}")
    print(f"  label: {data['label']}")
    assert 0 <= data["overall"] <= 100
    print("  PASS")


def test_8_openapi_has_all_routes():
    section("[8] OpenAPI spec — all routes present")
    r = httpx.get(f"{BASE}/openapi.json", timeout=5)
    assert r.status_code == 200
    spec = r.json()
    paths = list(spec.get("paths", {}).keys())

    required_paths = [
        "/api/v1/analyze",
        "/api/v1/collusion",
        "/api/v1/time-on-task",
        "/api/analyze/review",
        "/api/analyze/batch",
        "/api/scan/conference",
        "/api/scan/demo-venues",
        "/api/analyze/product-review",
        "/api/reviewer/{reviewer_id}",
        "/api/history/recent",
    ]

    for path in required_paths:
        assert path in paths, f"Missing path: {path}"
        print(f"  {path} ✓")
    print("  PASS")


def test_9_frontend_pages():
    section("[9] Frontend — all pages 200")
    pages = ["/", "/analyze", "/conference", "/methodology"]
    for page in pages:
        r = httpx.get(f"http://localhost:3000{page}", timeout=10)
        print(f"  {page}: {r.status_code}")
        assert r.status_code == 200
    print("  PASS")


if __name__ == "__main__":
    print("PHASE 5 END-TO-END INTEGRATION TEST")
    test_1_bakeoff_results()
    test_2_live_fire_demo_venues()
    test_3_live_fire_demo_scan()
    test_4_cross_track_product_review()
    test_5_spec_mismatch_detection()
    test_6_cli_version()
    test_7_cli_analyze()
    test_8_openapi_has_all_routes()
    test_9_frontend_pages()
    print(f"\n{'=' * 60}")
    print("  ALL PHASE 5 E2E TESTS PASSED")
    print("=" * 60)
