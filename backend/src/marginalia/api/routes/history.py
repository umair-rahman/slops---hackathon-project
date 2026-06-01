"""History endpoint — recent analyses from Postgres."""

from __future__ import annotations

from fastapi import APIRouter

from marginalia.data.db import db

router = APIRouter()


@router.get("/history/recent")
async def recent_analyses(limit: int = 10) -> dict:
    """Return the most recent analyses (last N)."""
    limit = max(1, min(limit, 100))
    rows = await db.recent_analyses(limit)
    return {"count": len(rows), "items": rows}
