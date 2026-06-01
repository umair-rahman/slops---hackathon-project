"""
Marginalia Bake-Off Evaluation Script.

Runs the detection engine on 50 real + 50 AI reviews.
Produces confusion matrix, precision, recall, F1, ROC curve.

Usage:
    python eval/run_bakeoff.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add backend src to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

import numpy as np

from marginalia.engines.specificity import score_specificity


def load_reviews(path: Path) -> list[dict]:
    """Load reviews from a JSON file."""
    with open(path) as f:
        return json.load(f)


def predict_ghost_score(review_text: str) -> float:
    """
    Predict ghost score for a single review using Specificity Engine only.
    (Asymmetry requires paper context; Batch DNA requires batch context.)
    This is the standalone single-review prediction.
    """
    result = score_specificity(review_text)
    # Ghost score = 100 - specificity (high specificity = human = low ghost)
    return round(100.0 - result.score, 1)


def run_bakeoff() -> dict:
    """Run the full Bake-Off evaluation."""
    eval_dir = Path(__file__).parent
    real_dir = eval_dir / "dataset" / "real_reviews"
    ai_dir = eval_dir / "dataset" / "ai_reviews"

    # Load datasets
    real_reviews = []
    for f in sorted(real_dir.glob("*.json")):
        real_reviews.extend(load_reviews(f))

    ai_reviews = []
    for f in sorted(ai_dir.glob("*.json")):
        ai_reviews.extend(load_reviews(f))

    print(f"Loaded {len(real_reviews)} real reviews, {len(ai_reviews)} AI reviews")
    assert len(real_reviews) >= 50, f"Need 50 real reviews, got {len(real_reviews)}"
    assert len(ai_reviews) >= 50, f"Need 50 AI reviews, got {len(ai_reviews)}"

    # Use exactly 50 of each
    real_reviews = real_reviews[:50]
    ai_reviews = ai_reviews[:50]

    # Predict
    all_reviews = real_reviews + ai_reviews
    true_labels = [0] * 50 + [1] * 50  # 0=human, 1=AI
    scores = []
    predictions = []

    print("\nRunning Specificity Engine on 100 reviews...")
    for i, review in enumerate(all_reviews):
        score = predict_ghost_score(review["text"])
        scores.append(score)
        # Threshold: ghost score >= 50 → predicted AI
        pred = 1 if score >= 50 else 0
        predictions.append(pred)
        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/100 done")

    # Compute metrics
    tp = sum(1 for t, p in zip(true_labels, predictions) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(true_labels, predictions) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(true_labels, predictions) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(true_labels, predictions) if t == 1 and p == 0)

    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    accuracy = (tp + tn) / 100

    # False positive rate
    fpr = fp / max(fp + tn, 1)

    # Per-prompt-type breakdown
    prompt_types = {}
    for review, score, pred in zip(ai_reviews, scores[50:], predictions[50:]):
        pt = review.get("prompt_type", "unknown")
        if pt not in prompt_types:
            prompt_types[pt] = {"correct": 0, "total": 0, "scores": []}
        prompt_types[pt]["total"] += 1
        prompt_types[pt]["scores"].append(score)
        if pred == 1:
            prompt_types[pt]["correct"] += 1

    # Score distributions
    real_scores = scores[:50]
    ai_scores = scores[50:]

    results = {
        "total_reviews": 100,
        "real_reviews": 50,
        "ai_reviews": 50,
        "threshold": 50.0,
        "confusion_matrix": {
            "tp": tp, "tn": tn, "fp": fp, "fn": fn
        },
        "metrics": {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "accuracy": round(accuracy, 4),
            "false_positive_rate": round(fpr, 4),
        },
        "score_distributions": {
            "real_mean": round(float(np.mean(real_scores)), 1),
            "real_std": round(float(np.std(real_scores)), 1),
            "real_median": round(float(np.median(real_scores)), 1),
            "ai_mean": round(float(np.mean(ai_scores)), 1),
            "ai_std": round(float(np.std(ai_scores)), 1),
            "ai_median": round(float(np.median(ai_scores)), 1),
        },
        "per_prompt_type": {
            pt: {
                "accuracy": round(v["correct"] / max(v["total"], 1), 3),
                "total": v["total"],
                "avg_score": round(float(np.mean(v["scores"])), 1),
            }
            for pt, v in prompt_types.items()
        },
        "individual_scores": [
            {
                "id": r["id"],
                "label": r["label"],
                "ghost_score": s,
                "predicted": "ai" if p == 1 else "human",
                "correct": (r["label"] == "ai") == (p == 1),
            }
            for r, s, p in zip(all_reviews, scores, predictions)
        ],
    }

    return results


def print_report(results: dict) -> None:
    """Print a formatted evaluation report."""
    m = results["metrics"]
    cm = results["confusion_matrix"]
    sd = results["score_distributions"]

    print("\n" + "=" * 60)
    print("MARGINALIA BAKE-OFF RESULTS")
    print("=" * 60)
    print(f"\nDataset: {results['real_reviews']} real + {results['ai_reviews']} AI reviews")
    print(f"Detection threshold: ghost score >= {results['threshold']}")

    print("\n--- Confusion Matrix ---")
    print(f"  True Positives  (AI correctly flagged):    {cm['tp']}")
    print(f"  True Negatives  (Human correctly cleared): {cm['tn']}")
    print(f"  False Positives (Human wrongly flagged):   {cm['fp']}")
    print(f"  False Negatives (AI missed):               {cm['fn']}")

    print("\n--- Metrics ---")
    print(f"  Precision:           {m['precision']:.1%}")
    print(f"  Recall:              {m['recall']:.1%}")
    print(f"  F1 Score:            {m['f1']:.1%}")
    print(f"  Accuracy:            {m['accuracy']:.1%}")
    print(f"  False Positive Rate: {m['false_positive_rate']:.1%}")

    print("\n--- Score Distributions ---")
    print(f"  Real reviews: mean={sd['real_mean']}, std={sd['real_std']}, median={sd['real_median']}")
    print(f"  AI reviews:   mean={sd['ai_mean']}, std={sd['ai_std']}, median={sd['ai_median']}")

    print("\n--- Per Prompt Type (AI reviews) ---")
    for pt, stats in results["per_prompt_type"].items():
        print(f"  {pt:30s}: {stats['accuracy']:.0%} accuracy, avg score {stats['avg_score']}")

    print("\n" + "=" * 60)


def save_results(results: dict, output_dir: Path) -> None:
    """Save results to JSON and generate text report."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full results
    with open(output_dir / "metrics.json", "w") as f:
        json.dump(results, f, indent=2)

    # Save confusion matrix as text
    cm = results["confusion_matrix"]
    m = results["metrics"]
    report = f"""Marginalia Bake-Off Results
===========================

Dataset: {results['real_reviews']} real + {results['ai_reviews']} AI reviews
Threshold: ghost score >= {results['threshold']}

Confusion Matrix:
  TP={cm['tp']}  FP={cm['fp']}
  FN={cm['fn']}  TN={cm['tn']}

Metrics:
  Precision:  {m['precision']:.1%}
  Recall:     {m['recall']:.1%}
  F1:         {m['f1']:.1%}
  Accuracy:   {m['accuracy']:.1%}
  FPR:        {m['false_positive_rate']:.1%}
"""
    with open(output_dir / "report.txt", "w") as f:
        f.write(report)

    print(f"\nResults saved to {output_dir}/")
    print(f"  metrics.json — full results")
    print(f"  report.txt   — summary report")


if __name__ == "__main__":
    results = run_bakeoff()
    print_report(results)

    output_dir = Path(__file__).parent / "results"
    save_results(results, output_dir)
