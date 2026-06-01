# Marginalia Backend

FastAPI backend for AI peer review detection.

See root [README.md](../README.md) for full documentation.

## Quick Start

```bash
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
uvicorn marginalia.main:app --reload
```
