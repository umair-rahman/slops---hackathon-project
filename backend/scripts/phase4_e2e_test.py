"""Phase 4 end-to-end integration test."""

import json
import time

import httpx

BASE = "http://127.0.0.1:8000"
NOW_MS = int(time.time() * 1000)
HOUR_MS = 3600 * 1000
MINUTE_MS = 60 * 1000

TEMPLATE = (
    "This paper presents {} contribution. The proposed method shows {} results. "
    "However, the experimental setup lacks detail. "
    "Overall, this is a solid paper. I recommend acceptance with minor revisions."
)


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def test_1_v1_health():
    section("[1] v1 Health endpoint")
    r = httpx.get(f"{BASE}/api/v1/health", timeout=5)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert len(data["endpoints"]) >= 3
    print(f"  endpoints: {data['endpoints']}")
    print("  PASS")


def test_2_v1_analyze():
    section("[2] v1 Analyze — AI review")
    ai_review = (
        "This paper presents an interesting contribution to the field. "
        "The methodology is well-described and the results are promising. "
        "The authors have done a good job. I recommend acceptance."
    )
    r = httpx.post(f"{BASE}/api/v1/analyze", json={"review_text": ai_review}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    print(f"  ghost score: {data['overall']} ({data['label']})")
    assert data["overall"] > 50
    print("  PASS")


def test_3_collusion_detection():
    section("[3] v1 Collusion Detection")
    reviews = [
        {"reviewer_id": "A", "review_text": TEMPLATE.format("an interesting", "promising")},
        {"reviewer_id": "B", "review_text": TEMPLATE.format("a novel", "competitive")},
        {"reviewer_id": "C", "review_text": TEMPLATE.format("a new", "strong")},
    ]
    r = httpx.post(
        f"{BASE}/api/v1/collusion",
        json={"paper_id": "paper_001", "reviews": reviews},
        timeout=15,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  collusion_detected: {data['collusion_detected']}")
    print(f"  collusion_score: {data['collusion_score']}")
    print(f"  flagged_pairs: {len(data['flagged_pairs'])}")
    assert data["collusion_detected"]
    assert len(data["flagged_pairs"]) >= 1
    print("  PASS")


def test_4_time_on_task_burst():
    section("[4] v1 Time-on-Task — burst detection")
    reviews = [
        {"review_id": f"r{i}", "review_text": " ".join(["word"] * 300),
         "timestamp_ms": NOW_MS + i * 30 * 1000}  # 30 seconds apart
        for i in range(4)
    ]
    r = httpx.post(
        f"{BASE}/api/v1/time-on-task",
        json={"reviewer_id": "reviewer_burst", "reviews": reviews},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  burst_detected: {data['burst_detected']}")
    print(f"  time_on_task_score: {data['time_on_task_score']}")
    print(f"  implausible_count: {data['implausible_count']}")
    assert data["burst_detected"]
    print("  PASS")


def test_5_time_on_task_plausible():
    section("[5] v1 Time-on-Task — plausible timing")
    reviews = [
        {"review_id": "r1", "review_text": " ".join(["word"] * 300), "timestamp_ms": NOW_MS},
        {"review_id": "r2", "review_text": " ".join(["word"] * 300), "timestamp_ms": NOW_MS + 2 * HOUR_MS},
    ]
    r = httpx.post(
        f"{BASE}/api/v1/time-on-task",
        json={"reviewer_id": "reviewer_ok", "reviews": reviews},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"  burst_detected: {data['burst_detected']}")
    print(f"  time_on_task_score: {data['time_on_task_score']}")
    assert not data["burst_detected"]
    print("  PASS")


def test_6_rate_limit_headers():
    section("[6] Rate limit headers present")
    r = httpx.post(
        f"{BASE}/api/v1/analyze",
        json={"review_text": "This paper presents an interesting contribution to the field. "
                             "The methodology is well-described. I recommend acceptance."},
        timeout=30,
    )
    assert r.status_code == 200
    print(f"  X-RateLimit-Limit: {r.headers.get('x-ratelimit-limit')}")
    print(f"  X-RateLimit-Remaining: {r.headers.get('x-ratelimit-remaining')}")
    assert r.headers.get("x-ratelimit-limit") is not None
    assert r.headers.get("x-ratelimit-remaining") is not None
    print("  PASS")


def test_7_docs_accessible():
    section("[7] OpenAPI docs accessible")
    r = httpx.get(f"{BASE}/docs", timeout=5)
    assert r.status_code == 200
    r2 = httpx.get(f"{BASE}/openapi.json", timeout=5)
    assert r2.status_code == 200
    spec = r2.json()
    paths = list(spec.get("paths", {}).keys())
    v1_paths = [p for p in paths if p.startswith("/api/v1/")]
    print(f"  v1 paths in spec: {v1_paths}")
    assert len(v1_paths) >= 3
    print("  PASS")


def test_8_validation_errors():
    section("[8] Input validation")
    # Too short
    r = httpx.post(f"{BASE}/api/v1/analyze", json={"review_text": "x"}, timeout=5)
    assert r.status_code == 422
    print(f"  short review: {r.status_code} (expected 422)")

    # Too long
    r = httpx.post(f"{BASE}/api/v1/analyze", json={"review_text": "x" * 10001}, timeout=5)
    assert r.status_code == 422
    print(f"  too long review: {r.status_code} (expected 422)")

    # Collusion with 1 review
    r = httpx.post(
        f"{BASE}/api/v1/collusion",
        json={"paper_id": "p", "reviews": [{"reviewer_id": "A", "review_text": "Some review text here."}]},
        timeout=5,
    )
    assert r.status_code == 422
    print(f"  single reviewer collusion: {r.status_code} (expected 422)")
    print("  PASS")


def test_9_frontend_pages():
    section("[9] Frontend pages all 200")
    pages = ["/", "/analyze", "/conference", "/methodology"]
    for page in pages:
        r = httpx.get(f"http://localhost:3000{page}", timeout=10)
        print(f"  {page}: {r.status_code}")
        assert r.status_code == 200
    print("  PASS")


if __name__ == "__main__":
    print("PHASE 4 END-TO-END INTEGRATION TEST")
    test_1_v1_health()
    test_2_v1_analyze()
    test_3_collusion_detection()
    test_4_time_on_task_burst()
    test_5_time_on_task_plausible()
    test_6_rate_limit_headers()
    test_7_docs_accessible()
    test_8_validation_errors()
    test_9_frontend_pages()
    print(f"\n{'=' * 60}")
    print("  ALL PHASE 4 E2E TESTS PASSED")
    print("=" * 60)
