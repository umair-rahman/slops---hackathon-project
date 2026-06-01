# Marginalia

> **Find what's missing in AI peer reviews.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org)

Marginalia detects AI-generated peer reviews via **3-layer signal triangulation**.
No LLM-as-judge. No keyword tricks. Just signal.

Built for [Slop Scan 2026](https://slopscan.dev) · Track F (Academia) · May 29 – Jun 1, 2026

---

## 🎯 The Problem

Academic peer review is breaking. Nature 2025 reported major AI conferences flooded with
fully AI-written reviews. Reviewers assigned 8 papers feed the same prompt to an LLM 8 times
and submit. The result: garbage feedback, random acceptance decisions, and a collapsing trust
in the scientific record.

**Nobody is building detection tools for this.** Marginalia does.

---

## 🔬 How It Works

### Layer 1 — Specificity Index
Real reviewers cite specifics: *"Equation 3.2 has a sign error"*, *"Figure 4(b) is unclear"*.
AI reviewers write: *"interesting contribution"*, *"methodology is well-described"*.

We extract academic anchors (equations, figures, sections, theorems, algorithms) and compute
anchor density per 100 words. Logistic-mapped to 0-100.

### Layer 2 — Asymmetry Score
AI reviewers are fed only the abstract. Their reviews reflect that.
Real reviewers reference body sections.

We embed the review and paper sections using `sentence-transformers/all-MiniLM-L6-v2`.
Asymmetry ratio = `sim_abstract / (sim_abstract + sim_body)`. High ratio → AI signal.

### Layer 3 — Batch DNA
A reviewer with 8 papers uses the same prompt 8 times. Output reviews share structural DNA:
paragraph count, sentence opener patterns, transition word density, punctuation rhythm.

We extract 16-dimensional fingerprints and cluster via greedy agglomeration.
Tight clusters = same prompt = AI batch.

### Aggregator
```
ghost_score = 0.40 × (100 - specificity)
            + 0.35 × asymmetry
            + 0.25 × batch_dna
```
Weights redistribute when layers are unavailable.

---

## 📊 Bake-Off Results

Evaluated on **50 real OpenReview reviews + 50 AI-generated reviews** (5 prompt types):

| Metric | Score |
|---|---|
| **Precision** | **87.0%** |
| **Recall** | **80.0%** |
| **F1 Score** | **83.3%** |
| **Accuracy** | **84.0%** |
| False Positive Rate | 12.0% |

*Specificity Engine only — no paper context, no batch context.*

---

## 🚀 Quick Start

### Backend

```bash
cd backend
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
cp ../.env.example .env  # fill in your credentials
uvicorn marginalia.main:app --reload
# → http://localhost:8000/docs
```

### Frontend

```bash
cd frontend
pnpm install --ignore-scripts
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
pnpm dev
# → http://localhost:3000
```

### CLI

```bash
pip install -e backend/
marginalia analyze "This paper presents an interesting contribution..."
marginalia analyze --file review.txt --json
marginalia scan ICLR.cc/2024/Conference
marginalia version
```

### Docker (local stack)

```bash
cp .env.example .env
docker-compose up
```

---

## 🌐 Live Demo

- **Frontend:** https://marginalia-ai.vercel.app
- **API:** https://marginalia-api.fly.dev
- **API Docs:** https://marginalia-api.fly.dev/docs

---

## 📡 API Reference

### Public API v1

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/health` | Health check + endpoint list |
| POST | `/api/v1/analyze` | Analyze a review (rate limited: 20/min) |
| POST | `/api/v1/collusion` | Detect cross-reviewer collusion |
| POST | `/api/v1/time-on-task` | Estimate submission timing plausibility |

### Internal API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/analyze/review` | Full analysis with DB persistence |
| POST | `/api/analyze/batch` | Batch analysis with DNA clustering |
| GET | `/api/scan/conference` | SSE venue scan |
| GET | `/api/scan/demo-venues` | List pre-cached demo venues |
| GET | `/api/reviewer/{id}` | Reviewer profile + drift detection |
| GET | `/api/history/recent` | Recent analyses from Postgres |
| POST | `/api/analyze/product-review` | Track G cross-track extension |

### Example

```bash
curl -X POST https://marginalia-api.fly.dev/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"review_text": "This paper presents an interesting contribution..."}'
```

```json
{
  "overall": 92.4,
  "label": "almost certainly AI-generated",
  "confidence_low": 84.4,
  "confidence_high": 100.0,
  "specificity": {"score": 7.6, "total_anchors": 0},
  "explanation": "Ghost score 92.4/100 — the review contains almost no specific references..."
}
```

---

## 🏗️ Architecture

```
marginalia/
├── backend/                    FastAPI + Python 3.11
│   └── src/marginalia/
│       ├── engines/            Detection engines
│       │   ├── specificity.py  Layer 1: anchor density
│       │   ├── asymmetry.py    Layer 2: content grounding
│       │   ├── batch_dna.py    Layer 3: structural clustering
│       │   ├── aggregator.py   Ghost score combiner
│       │   ├── collusion.py    Cross-reviewer detection
│       │   ├── style_drift.py  Reviewer drift detection
│       │   ├── time_on_task.py Timing plausibility
│       │   └── product_review.py Track G cross-track
│       ├── data/               External data clients
│       │   ├── openreview.py   OpenReview API + cache
│       │   ├── arxiv.py        arXiv API + cache
│       │   ├── cache.py        Upstash Redis REST
│       │   ├── db.py           Neon Postgres
│       │   └── demo_cache.py   Live Fire pre-cached data
│       ├── api/routes/         FastAPI endpoints
│       └── middleware/         Rate limiting
├── frontend/                   Next.js 16 + Tailwind v4
│   └── app/
│       ├── page.tsx            Landing page
│       ├── analyze/            Single review analysis
│       ├── conference/         Venue scan dashboard
│       ├── reviewer/[id]/      Reviewer profile
│       └── methodology/        Detection explainer
└── eval/                       Bake-Off evaluation
    ├── dataset/                50 real + 50 AI reviews
    ├── run_bakeoff.py          Evaluation script
    └── results/metrics.json    Results
```

---

## 🧪 Testing

```bash
# Unit tests (116 tests)
cd backend
python -m pytest tests/ -q

# Phase-specific E2E tests
python scripts/phase5_e2e_test.py

# Bake-Off evaluation
python eval/run_bakeoff.py
```

---

## 🔧 Tech Stack

| Component | Choice |
|---|---|
| Backend | FastAPI 0.115 + Python 3.11 |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` |
| Clustering | Custom union-find (HDBSCAN-ready) |
| PDF parsing | PyMuPDF |
| Data | OpenReview API · arXiv API · Semantic Scholar |
| Cache | Upstash Redis (REST) |
| Database | Neon Postgres |
| Frontend | Next.js 16 · Tailwind v4 · Recharts |
| Hosting | Vercel (frontend) · Fly.io (backend) |

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## 📄 License

MIT © 2026 Marginalia Team

---

## 🏆 Hackathon

Built for [Slop Scan 2026](https://slopscan.dev) · Track F (Academia)

> *"Slop" was the 2025 Word of the Year. The internet has a quality problem.
> You have 72 hours. — slopscan.dev*
