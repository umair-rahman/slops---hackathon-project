"""
Phase 6 Final Verification Script.

Verifies everything is production-ready for hackathon submission.
"""

import json
import subprocess
import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
FRONTEND = "http://localhost:3000"
ROOT = Path(__file__).parent.parent.parent.parent / "marginalia"


def check(name: str, passed: bool, detail: str = "") -> bool:
    status = "PASS" if passed else "FAIL"
    icon = "OK" if passed else "!!"
    print(f"  [{icon}] {name}" + (f" — {detail}" if detail else ""))
    return passed


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print("=" * 60)


def main() -> None:
    print("MARGINALIA — PHASE 6 FINAL VERIFICATION")
    print("=" * 60)

    all_passed = True

    # ── 1. File Structure ────────────────────────────────────────────────────
    section("[1] Project File Structure")
    required_files = [
        "README.md",
        "LICENSE",
        "CONTRIBUTING.md",
        ".gitignore",
        "docker-compose.yml",
        ".env.example",
        "backend/pyproject.toml",
        "backend/Dockerfile",
        "backend/fly.toml",
        "backend/src/marginalia/main.py",
        "backend/src/marginalia/engines/specificity.py",
        "backend/src/marginalia/engines/asymmetry.py",
        "backend/src/marginalia/engines/batch_dna.py",
        "backend/src/marginalia/engines/aggregator.py",
        "backend/src/marginalia/engines/collusion.py",
        "backend/src/marginalia/engines/style_drift.py",
        "backend/src/marginalia/engines/time_on_task.py",
        "backend/src/marginalia/engines/product_review.py",
        "backend/src/marginalia/engines/pipeline.py",
        "backend/src/marginalia/data/openreview.py",
        "backend/src/marginalia/data/arxiv.py",
        "backend/src/marginalia/data/cache.py",
        "backend/src/marginalia/data/db.py",
        "backend/src/marginalia/data/demo_cache.py",
        "backend/src/marginalia/api/routes/analyze.py",
        "backend/src/marginalia/api/routes/conference.py",
        "backend/src/marginalia/api/routes/reviewer.py",
        "backend/src/marginalia/api/routes/history.py",
        "backend/src/marginalia/api/routes/v1.py",
        "backend/src/marginalia/api/routes/crosstrack.py",
        "backend/src/marginalia/middleware/rate_limit.py",
        "backend/src/marginalia/cli.py",
        "frontend/app/page.tsx",
        "frontend/app/analyze/page.tsx",
        "frontend/app/conference/page.tsx",
        "frontend/app/methodology/page.tsx",
        "frontend/components/GhostScoreCard.tsx",
        "frontend/components/SpecificityHeatmap.tsx",
        "frontend/components/LayerBreakdown.tsx",
        "frontend/components/ClusterMap.tsx",
        "frontend/components/ScoreHistogram.tsx",
        "frontend/components/DriftTimeline.tsx",
        "frontend/components/HallucinationBadge.tsx",
        "frontend/components/ShareCard.tsx",
        "frontend/vercel.json",
        "eval/run_bakeoff.py",
        "eval/dataset/real_reviews/reviews.json",
        "eval/dataset/ai_reviews/reviews.json",
        "eval/results/metrics.json",
        "docs/DEPLOYMENT.md",
        "docs/DEMO_SCRIPT.md",
    ]

    for f in required_files:
        exists = (ROOT / f).exists()
        if not check(f, exists):
            all_passed = False

    # ── 2. Backend Health ────────────────────────────────────────────────────
    section("[2] Backend Health")
    try:
        r = httpx.get(f"{BASE}/health", timeout=5)
        ok = r.status_code == 200 and r.json()["status"] == "ok"
        if not check("GET /health → 200", ok, r.json().get("version", "")):
            all_passed = False
    except Exception as e:
        check("GET /health → 200", False, str(e))
        all_passed = False

    # ── 3. All API Routes ────────────────────────────────────────────────────
    section("[3] API Routes")
    try:
        r = httpx.get(f"{BASE}/openapi.json", timeout=5)
        paths = list(r.json().get("paths", {}).keys())
        required_routes = [
            "/api/v1/health", "/api/v1/analyze", "/api/v1/collusion",
            "/api/v1/time-on-task", "/api/analyze/review", "/api/analyze/batch",
            "/api/scan/conference", "/api/scan/demo-venues",
            "/api/analyze/product-review", "/api/reviewer/{reviewer_id}",
            "/api/history/recent",
        ]
        for route in required_routes:
            ok = route in paths
            if not check(route, ok):
                all_passed = False
    except Exception as e:
        check("OpenAPI spec", False, str(e))
        all_passed = False

    # ── 4. Core Detection ────────────────────────────────────────────────────
    section("[4] Core Detection Accuracy")
    try:
        ai_review = (
            "This paper presents an interesting contribution. "
            "The methodology is well-described. I recommend acceptance."
        )
        r = httpx.post(f"{BASE}/api/analyze/review", json={"review_text": ai_review}, timeout=30)
        data = r.json()
        ok = r.status_code == 200 and data["overall"] > 50
        if not check("AI review → ghost > 50", ok, f"score={data.get('overall')}"):
            all_passed = False

        human_review = (
            "Equation 5 in Section 3.2 has a sign error. Figure 4(b) is unclear. "
            "Table 2 is missing confidence intervals. Algorithm 1 on page 8 has a bug."
        )
        r = httpx.post(f"{BASE}/api/analyze/review", json={"review_text": human_review}, timeout=30)
        data = r.json()
        ok = r.status_code == 200 and data["overall"] < 50
        if not check("Human review → ghost < 50", ok, f"score={data.get('overall')}"):
            all_passed = False
    except Exception as e:
        check("Detection accuracy", False, str(e))
        all_passed = False

    # ── 5. Bake-Off Results ──────────────────────────────────────────────────
    section("[5] Bake-Off Results")
    try:
        metrics_file = ROOT / "eval" / "results" / "metrics.json"
        data = json.loads(metrics_file.read_text())
        m = data["metrics"]
        if not check("F1 > 0.80", m["f1"] > 0.80, f"F1={m['f1']:.1%}"):
            all_passed = False
        if not check("Precision > 0.80", m["precision"] > 0.80, f"Precision={m['precision']:.1%}"):
            all_passed = False
        if not check("Accuracy > 0.80", m["accuracy"] > 0.80, f"Accuracy={m['accuracy']:.1%}"):
            all_passed = False
    except Exception as e:
        check("Bake-Off metrics", False, str(e))
        all_passed = False

    # ── 6. Live Fire Demo ────────────────────────────────────────────────────
    section("[6] Live Fire Demo Mode")
    try:
        r = httpx.get(f"{BASE}/api/scan/demo-venues", timeout=5)
        venues = r.json()["venues"]
        ok = "ICLR.cc/2024/Conference" in venues
        if not check("Demo venues available", ok, f"{len(venues)} venues"):
            all_passed = False
    except Exception as e:
        check("Demo venues", False, str(e))
        all_passed = False

    # ── 7. CLI ───────────────────────────────────────────────────────────────
    section("[7] CLI")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "marginalia.cli", "version"],
            capture_output=True, text=True,
            cwd=str(ROOT / "backend"),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        ok = result.returncode == 0 and "marginalia-ai" in result.stdout
        if not check("marginalia version", ok, result.stdout.strip()):
            all_passed = False

        result = subprocess.run(
            [sys.executable, "-m", "marginalia.cli", "analyze", "--json",
             "This paper presents an interesting contribution. The methodology is clear."],
            capture_output=True, text=True,
            cwd=str(ROOT / "backend"),
            env={**__import__("os").environ, "PYTHONPATH": "src"},
        )
        ok = result.returncode == 0
        if ok:
            data = json.loads(result.stdout)
            ok = 0 <= data["overall"] <= 100
        if not check("marginalia analyze --json", ok):
            all_passed = False
    except Exception as e:
        check("CLI", False, str(e))
        all_passed = False

    # ── 8. Cross-Track ───────────────────────────────────────────────────────
    section("[8] Cross-Track (Track G)")
    try:
        r = httpx.post(
            f"{BASE}/api/analyze/product-review",
            json={"review_text": "Great product! Highly recommend. Works as expected. Good quality."},
            timeout=10,
        )
        ok = r.status_code == 200 and r.json()["ghost_score"] > 50
        if not check("Product review detection", ok, f"score={r.json().get('ghost_score')}"):
            all_passed = False
    except Exception as e:
        check("Cross-track", False, str(e))
        all_passed = False

    # ── 9. Frontend ──────────────────────────────────────────────────────────
    section("[9] Frontend Pages")
    pages = ["/", "/analyze", "/conference", "/methodology"]
    for page in pages:
        try:
            r = httpx.get(f"{FRONTEND}{page}", timeout=10)
            ok = r.status_code == 200
            if not check(f"GET {page} → 200", ok):
                all_passed = False
        except Exception as e:
            check(f"GET {page}", False, str(e))
            all_passed = False

    # ── 10. Git Status ───────────────────────────────────────────────────────
    section("[10] Git Repository")
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        ok = result.returncode == 0 and len(result.stdout.strip()) > 0
        if not check("Git commit exists", ok, result.stdout.strip()):
            all_passed = False

        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        ok = result.returncode == 0 and result.stdout.strip() == ""
        if not check("Working tree clean", ok):
            all_passed = False
    except Exception as e:
        check("Git", False, str(e))
        all_passed = False

    # ── Summary ──────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    if all_passed:
        print("  ALL CHECKS PASSED — READY FOR SUBMISSION")
    else:
        print("  SOME CHECKS FAILED — FIX BEFORE SUBMITTING")
    print("=" * 60)

    # Submission checklist
    print("\nSUBMISSION CHECKLIST:")
    print("  [x] Working tool — local + demo mode")
    print("  [x] Source code — git repo initialized")
    print("  [x] README — comprehensive with screenshots")
    print("  [x] Bake-Off — F1=83.3%, Precision=87%")
    print("  [x] Live Fire — 3 pre-cached venues")
    print("  [x] Open Source Ready — CLI + pyproject.toml")
    print("  [x] Cross-Track — Track G product reviews")
    print("  [ ] Demo video — record 3-min video (see docs/DEMO_SCRIPT.md)")
    print("  [ ] GitHub repo public — push to github.com/marginalia-ai/marginalia")
    print("  [ ] Fly.io deploy — flyctl auth login && flyctl deploy")
    print("  [ ] Vercel deploy — vercel login && vercel --prod")
    print("  [ ] Submit form — https://slopscan.dev")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
