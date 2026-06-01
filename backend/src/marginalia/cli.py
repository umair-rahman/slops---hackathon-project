"""
Marginalia CLI — Command-line interface for AI peer review detection.

Usage:
    marginalia analyze "Review text here..."
    marginalia analyze --file review.txt
    marginalia analyze --file review.txt --arxiv 1706.03762
    marginalia scan ICLR.cc/2024/Conference
    marginalia scan ICLR.cc/2024/Conference --max-papers 50
    marginalia bakeoff
    marginalia version
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


def cmd_analyze(args: argparse.Namespace) -> None:
    """Analyze a single peer review."""
    # Get review text
    if args.file:
        review_text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        review_text = args.text
    else:
        print("Reading review from stdin (Ctrl+D to finish)...")
        review_text = sys.stdin.read()

    if len(review_text.strip()) < 20:
        print("Error: Review text must be at least 20 characters.", file=sys.stderr)
        sys.exit(1)

    # Import here to avoid slow startup for --help
    from marginalia.engines.specificity import score_specificity
    from marginalia.engines.aggregator import compute_ghost_score
    from marginalia.engines.asymmetry import AsymmetryResult
    from marginalia.engines.batch_dna import BatchDNAResult

    spec = score_specificity(review_text)
    asym = AsymmetryResult(
        score=0.0, sim_abstract=0.0, sim_body=0.0,
        asymmetry_ratio=0.0, hallucinated_sentences=[]
    )
    ghost = compute_ghost_score(spec, asym, None, len(review_text.split()))

    if args.json:
        output = {
            "overall": ghost.overall,
            "label": ghost.label,
            "confidence_low": ghost.confidence_low,
            "confidence_high": ghost.confidence_high,
            "specificity_score": spec.score,
            "total_anchors": spec.total_anchors,
            "anchors_per_100_words": spec.anchors_per_100_words,
            "explanation": ghost.explanation,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\nMarginalia Ghost Score Analysis")
        print(f"{'=' * 40}")
        print(f"Ghost Score:    {ghost.overall}/100")
        print(f"Verdict:        {ghost.label}")
        print(f"Confidence:     {ghost.confidence_low} – {ghost.confidence_high}")
        print(f"Specificity:    {spec.score}/100 ({spec.total_anchors} anchors)")
        print(f"\nExplanation: {ghost.explanation}")

        if spec.total_anchors > 0:
            print(f"\nAnchors found:")
            for sent in spec.sentences:
                if sent.anchors:
                    for anchor in sent.anchors:
                        print(f"  [{anchor.anchor_type}] {anchor.text}")


def cmd_scan(args: argparse.Namespace) -> None:
    """Scan a conference venue."""
    async def _scan():
        from marginalia.data.openreview import openreview_client
        from marginalia.data.demo_cache import get_demo_venue
        from marginalia.engines.specificity import score_specificity
        from marginalia.engines.batch_dna import score_batch_dna

        venue_id = args.venue_id
        max_papers = args.max_papers

        print(f"Scanning {venue_id} (max {max_papers} papers)...")

        # Try demo cache first
        demo = get_demo_venue(venue_id)
        reviews = await openreview_client.get_reviews(venue_id, max_papers)

        if not reviews and demo:
            print("Using pre-cached demo data.")
            if args.json:
                print(json.dumps(demo, indent=2))
            else:
                print(f"\nVenue: {demo['venue_id']}")
                print(f"Reviews: {demo['total_reviews']}")
                print(f"Flagged: {demo['flagged_percent']}%")
                print(f"Collusion pairs: {demo.get('collusion_count', 0)}")
            return

        if not reviews:
            print(f"No reviews found for {venue_id}. Check venue ID.", file=sys.stderr)
            sys.exit(1)

        print(f"Fetched {len(reviews)} reviews. Analyzing...")

        scores = []
        for r in reviews:
            spec = score_specificity(r.review_text)
            ghost = 100.0 - spec.score
            scores.append(ghost)

        flagged = sum(1 for s in scores if s >= 65)
        avg = sum(scores) / len(scores) if scores else 0

        if args.json:
            output = {
                "venue_id": venue_id,
                "total_reviews": len(reviews),
                "flagged_count": flagged,
                "flagged_percent": round(flagged / len(reviews) * 100, 1),
                "avg_ghost_score": round(avg, 1),
            }
            print(json.dumps(output, indent=2))
        else:
            print(f"\nVenue Scan Results: {venue_id}")
            print(f"{'=' * 40}")
            print(f"Reviews scanned: {len(reviews)}")
            print(f"Flagged (ghost >= 65): {flagged} ({flagged/len(reviews)*100:.1f}%)")
            print(f"Average ghost score: {avg:.1f}")

    asyncio.run(_scan())


def cmd_bakeoff(args: argparse.Namespace) -> None:
    """Run the Bake-Off evaluation."""
    eval_script = Path(__file__).parent.parent.parent.parent / "eval" / "run_bakeoff.py"
    if not eval_script.exists():
        print(f"Bake-Off script not found at {eval_script}", file=sys.stderr)
        sys.exit(1)

    import subprocess
    result = subprocess.run([sys.executable, str(eval_script)], check=False)
    sys.exit(result.returncode)


def cmd_version(args: argparse.Namespace) -> None:
    """Print version."""
    from marginalia import __version__
    print(f"marginalia-ai {__version__}")


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="marginalia",
        description="Marginalia — AI peer review detection",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    # analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analyze a single review")
    analyze_group = analyze_parser.add_mutually_exclusive_group()
    analyze_group.add_argument("text", nargs="?", help="Review text (inline)")
    analyze_group.add_argument("--file", "-f", help="Path to review text file")
    analyze_parser.add_argument("--arxiv", help="arXiv paper ID for asymmetry analysis")
    analyze_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan a conference venue")
    scan_parser.add_argument("venue_id", help="OpenReview venue ID")
    scan_parser.add_argument("--max-papers", type=int, default=50, help="Max papers to scan")
    scan_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # bakeoff
    subparsers.add_parser("bakeoff", help="Run Bake-Off evaluation")

    # version
    subparsers.add_parser("version", help="Print version")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "bakeoff":
        cmd_bakeoff(args)
    elif args.command == "version":
        cmd_version(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
