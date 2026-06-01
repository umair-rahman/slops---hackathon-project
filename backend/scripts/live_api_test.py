"""Live API test against running server."""

import json

import httpx

BASE = "http://127.0.0.1:8000"

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
    "Table 2 is missing confidence intervals. In Section 5.1, the accuracy claim "
    "contradicts Figure 6. Algorithm 1 on page 8 has an off-by-one error in the loop bounds."
)


def test_health():
    r = httpx.get(f"{BASE}/health", timeout=10)
    assert r.status_code == 200
    print(f"[1] /health -> {r.status_code} {r.json()}")


def test_analyze_ai():
    r = httpx.post(
        f"{BASE}/api/analyze/review",
        json={"review_text": AI_REVIEW},
        timeout=30,
    )
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    data = r.json()
    print(f"[2] AI Review:")
    print(f"    overall: {data['overall']}  label: {data['label']}")
    print(f"    specificity: {data['specificity']['score']}  anchors: {data['specificity']['total_anchors']}")
    print(f"    asymmetry: {data['asymmetry']['score']}")
    print(f"    explanation: {data['explanation'][:80]}...")
    assert data["overall"] > 50, f"AI review should score > 50, got {data['overall']}"


def test_analyze_human():
    r = httpx.post(
        f"{BASE}/api/analyze/review",
        json={"review_text": HUMAN_REVIEW},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    print(f"[3] Human Review:")
    print(f"    overall: {data['overall']}  label: {data['label']}")
    print(f"    specificity: {data['specificity']['score']}  anchors: {data['specificity']['total_anchors']}")
    print(f"    explanation: {data['explanation'][:80]}...")
    assert data["overall"] < 50, f"Human review should score < 50, got {data['overall']}"


def test_validation():
    r = httpx.post(f"{BASE}/api/analyze/review", json={"review_text": "tiny"}, timeout=10)
    assert r.status_code == 422
    print(f"[4] Short review validation: {r.status_code} (rejected as expected)")


def test_batch():
    template = (
        "This paper presents {} contribution. The proposed method shows {} results. "
        "However, the experimental setup lacks detail. "
        "Overall, this is a solid paper. I recommend acceptance with minor revisions."
    )
    reviews = [
        {"review_id": "r1", "review_text": template.format("an interesting", "promising")},
        {"review_id": "r2", "review_text": template.format("a novel", "competitive")},
        {"review_id": "r3", "review_text": template.format("a new", "strong")},
    ]
    r = httpx.post(f"{BASE}/api/analyze/batch", json={"reviews": reviews}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    print(f"[5] Batch analysis ({len(data)} reviews):")
    for i, item in enumerate(data):
        print(
            f"    r{i+1}: overall={item['overall']}  cluster_size={item['batch_dna']['cluster_size']}  available={item['batch_dna']['available']}"
        )
    has_cluster = any(r["batch_dna"]["cluster_size"] and r["batch_dna"]["cluster_size"] >= 2 for r in data)
    assert has_cluster, "AI batch should produce a cluster"


def test_sse_scan():
    with httpx.stream(
        "GET",
        f"{BASE}/api/scan/conference?venue_id=NONEXISTENT/Venue&max_papers=1",
        timeout=15,
    ) as r:
        assert r.status_code == 200
        events = []
        for line in r.iter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
            if len(events) >= 8:
                break
        assert len(events) >= 1
        print(f"[6] SSE scan: received {len(events)} events")
        for e in events[:3]:
            print(f"    {e.get('type')}: {e.get('message') or e.get('error') or '(complete)'}")


if __name__ == "__main__":
    print("=" * 60)
    print("LIVE API INTEGRATION TEST")
    print("=" * 60)
    test_health()
    test_analyze_ai()
    test_analyze_human()
    test_validation()
    test_batch()
    test_sse_scan()
    print("=" * 60)
    print("ALL LIVE API TESTS PASSED")
    print("=" * 60)
