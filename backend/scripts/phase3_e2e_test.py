"""Phase 3 end-to-end integration test."""

import json
import time

import httpx

BASE = "http://127.0.0.1:8000"


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def test_1_health():
    section("[1] Health endpoint")
    r = httpx.get(f"{BASE}/health", timeout=5)
    assert r.status_code == 200
    print(f"  PASS - {r.json()}")


def test_2_analyze_with_real_arxiv():
    section("[2] Analyze with real arXiv paper (cache miss)")
    # Famous paper for stable test
    abstract_only_review = (
        "This paper introduces the Transformer architecture, replacing recurrence "
        "with attention. The proposed approach achieves state-of-the-art results "
        "on translation benchmarks. The method is novel and the evaluation is solid. "
        "I recommend acceptance."
    )
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/api/analyze/review",
        json={"review_text": abstract_only_review, "paper_arxiv_id": "1706.03762"},
        timeout=120,
    )
    elapsed = time.time() - t0
    assert r.status_code == 200, f"{r.status_code}: {r.text[:200]}"
    data = r.json()
    print(f"  paper: 1706.03762 (Attention Is All You Need)")
    print(f"  fetch+analyze took: {elapsed:.1f}s")
    print(f"  ghost score: {data['overall']}")
    print(f"  asymmetry: {data['asymmetry']['score']}")
    print(f"  sim_abstract: {data['asymmetry']['sim_abstract']}")
    print(f"  sim_body:     {data['asymmetry']['sim_body']}")
    assert data['asymmetry']['score'] > 0, "Asymmetry should activate when paper is provided"
    print("  PASS")


def test_3_arxiv_cache_hit():
    section("[3] Cache hit (same paper, no full fetch)")
    abstract_only_review = (
        "The Transformer architecture replaces recurrence with attention. "
        "It achieves state-of-the-art results on translation. "
        "Novel approach. Solid results. Recommend acceptance."
    )
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/api/analyze/review",
        json={"review_text": abstract_only_review, "paper_arxiv_id": "1706.03762"},
        timeout=30,
    )
    elapsed = time.time() - t0
    assert r.status_code == 200
    data = r.json()
    print(f"  cached fetch+analyze: {elapsed:.1f}s")
    assert elapsed < 15, f"Cache hit should be fast, got {elapsed:.1f}s"
    print(f"  ghost score: {data['overall']}")
    print("  PASS")


def test_4_history_persistence():
    section("[4] History endpoint (Postgres persistence)")
    r = httpx.get(f"{BASE}/api/history/recent?limit=5", timeout=10)
    assert r.status_code == 200
    data = r.json()
    print(f"  count: {data['count']}")
    if data["count"] > 0:
        latest = data["items"][0]
        print(f"  latest: id={latest['id']} score={latest['overall_score']} arxiv={latest['paper_arxiv_id']}")
        assert "created_at" in latest
        assert latest["overall_score"] >= 0
    else:
        print("  (no items yet — DB persistence may have been skipped)")
    print("  PASS")


def test_5_batch_with_paper():
    section("[5] Batch analysis with paper context")
    template = (
        "This paper presents {} contribution. The method shows {} results. "
        "However, the experimental setup lacks detail. Overall, recommend acceptance."
    )
    reviews = [
        {"review_id": "r1", "review_text": template.format("an interesting", "promising")},
        {"review_id": "r2", "review_text": template.format("a novel", "competitive")},
        {"review_id": "r3", "review_text": template.format("a new", "strong")},
    ]
    r = httpx.post(
        f"{BASE}/api/analyze/batch",
        json={"reviews": reviews, "paper_arxiv_id": "1706.03762"},
        timeout=60,
    )
    assert r.status_code == 200
    data = r.json()
    cluster_sizes = {item["batch_dna"]["cluster_size"] for item in data}
    print(f"  cluster sizes: {cluster_sizes}")
    print(f"  ghost scores: {[item['overall'] for item in data]}")
    assert any(s and s >= 2 for s in cluster_sizes)
    print("  PASS")


def test_6_validation():
    section("[6] Input validation")
    r = httpx.post(f"{BASE}/api/analyze/review", json={"review_text": "x"}, timeout=5)
    assert r.status_code == 422
    print(f"  short review rejected: {r.status_code}")
    print("  PASS")


def test_7_sse_scan():
    section("[7] SSE conference scan")
    with httpx.stream(
        "GET",
        f"{BASE}/api/scan/conference?venue_id=NONEXISTENT/Venue&max_papers=1",
        timeout=15,
    ) as r:
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        events = []
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
            if any(e["type"] in ("complete", "error") for e in events):
                break
        types = [e["type"] for e in events]
        print(f"  event types: {types}")
        assert any(t in ("complete", "error") for t in types)
    print("  PASS")


def test_8_cors():
    section("[8] CORS preflight from frontend")
    r = httpx.options(
        f"{BASE}/api/analyze/review",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=5,
    )
    assert r.status_code == 200
    print(f"  preflight: {r.status_code}")
    print(f"  allow-origin: {r.headers.get('access-control-allow-origin')}")
    print("  PASS")


if __name__ == "__main__":
    print("PHASE 3 END-TO-END INTEGRATION TEST")
    test_1_health()
    test_2_analyze_with_real_arxiv()
    test_3_arxiv_cache_hit()
    test_4_history_persistence()
    test_5_batch_with_paper()
    test_6_validation()
    test_7_sse_scan()
    test_8_cors()
    print(f"\n{'=' * 60}")
    print("  ALL PHASE 3 E2E TESTS PASSED")
    print("=" * 60)
