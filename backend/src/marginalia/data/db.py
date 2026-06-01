"""
Postgres database layer for persisting analysis history + audit log.

Uses asyncpg (preferred) or psycopg2 fallback, with optional disable for local dev.
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from marginalia.config import settings

logger = logging.getLogger(__name__)


CREATE_ANALYSES_TABLE = """
CREATE TABLE IF NOT EXISTS analyses (
    id SERIAL PRIMARY KEY,
    review_text_hash VARCHAR(64) NOT NULL,
    paper_arxiv_id VARCHAR(64),
    overall_score REAL NOT NULL,
    label VARCHAR(64) NOT NULL,
    specificity_score REAL NOT NULL,
    asymmetry_score REAL NOT NULL,
    batch_dna_score REAL,
    word_count INTEGER NOT NULL,
    explanation TEXT,
    full_result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_analyses_hash ON analyses(review_text_hash);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
"""


CREATE_VENUE_SCANS_TABLE = """
CREATE TABLE IF NOT EXISTS venue_scans (
    id SERIAL PRIMARY KEY,
    venue_id VARCHAR(255) NOT NULL,
    total_papers INTEGER NOT NULL,
    total_reviews INTEGER NOT NULL,
    flagged_count INTEGER NOT NULL,
    flagged_percent REAL NOT NULL,
    avg_score REAL NOT NULL,
    full_result JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_venue_scans_venue ON venue_scans(venue_id);
"""


class Database:
    """Postgres connection manager. Synchronous via psycopg2 in thread pool."""

    def __init__(self, url: str) -> None:
        self.url = url
        self._enabled = bool(url) and url.startswith("postgresql")
        self._initialized = False

    async def init(self) -> None:
        if not self._enabled or self._initialized:
            return

        try:
            await asyncio.get_event_loop().run_in_executor(None, self._init_sync)
            self._initialized = True
            logger.info("Database tables initialized")
        except Exception as e:
            logger.warning(f"DB init failed: {e}")
            self._enabled = False

    def _init_sync(self) -> None:
        import psycopg2

        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor() as cur:
                cur.execute(CREATE_ANALYSES_TABLE)
                cur.execute(CREATE_VENUE_SCANS_TABLE)
            conn.commit()
        finally:
            conn.close()

    async def insert_analysis(
        self,
        review_text_hash: str,
        paper_arxiv_id: str | None,
        ghost_data: dict,
        word_count: int,
    ) -> int | None:
        if not self._enabled:
            return None

        try:
            return await asyncio.get_event_loop().run_in_executor(
                None,
                self._insert_analysis_sync,
                review_text_hash,
                paper_arxiv_id,
                ghost_data,
                word_count,
            )
        except Exception as e:
            logger.warning(f"DB insert_analysis failed: {e}")
            return None

    def _insert_analysis_sync(
        self,
        review_text_hash: str,
        paper_arxiv_id: str | None,
        ghost_data: dict,
        word_count: int,
    ) -> int:
        import psycopg2

        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO analyses
                    (review_text_hash, paper_arxiv_id, overall_score, label,
                     specificity_score, asymmetry_score, batch_dna_score,
                     word_count, explanation, full_result)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        review_text_hash,
                        paper_arxiv_id,
                        ghost_data["overall"],
                        ghost_data["label"],
                        ghost_data["specificity"]["score"],
                        ghost_data["asymmetry"]["score"],
                        ghost_data["batch_dna"].get("score"),
                        word_count,
                        ghost_data["explanation"],
                        json.dumps(ghost_data),
                    ),
                )
                analysis_id = cur.fetchone()[0]
            conn.commit()
            return analysis_id
        finally:
            conn.close()

    async def insert_venue_scan(self, venue_id: str, scan_data: dict) -> int | None:
        if not self._enabled:
            return None

        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._insert_venue_scan_sync, venue_id, scan_data
            )
        except Exception as e:
            logger.warning(f"DB insert_venue_scan failed: {e}")
            return None

    def _insert_venue_scan_sync(self, venue_id: str, scan_data: dict) -> int:
        import psycopg2

        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO venue_scans
                    (venue_id, total_papers, total_reviews, flagged_count,
                     flagged_percent, avg_score, full_result)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        venue_id,
                        scan_data.get("total_papers", 0),
                        scan_data.get("total_reviews", 0),
                        scan_data.get("flagged_count", 0),
                        scan_data.get("flagged_percent", 0.0),
                        scan_data.get("avg_score", 0.0),
                        json.dumps(scan_data),
                    ),
                )
                scan_id = cur.fetchone()[0]
            conn.commit()
            return scan_id
        finally:
            conn.close()

    async def recent_analyses(self, limit: int = 10) -> list[dict]:
        if not self._enabled:
            return []
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, self._recent_analyses_sync, limit
            )
        except Exception as e:
            logger.warning(f"DB recent_analyses failed: {e}")
            return []

    def _recent_analyses_sync(self, limit: int) -> list[dict]:
        import psycopg2

        conn = psycopg2.connect(self.url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, paper_arxiv_id, overall_score, label,
                           specificity_score, asymmetry_score, batch_dna_score,
                           created_at
                    FROM analyses
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "paper_arxiv_id": r[1],
                        "overall_score": r[2],
                        "label": r[3],
                        "specificity_score": r[4],
                        "asymmetry_score": r[5],
                        "batch_dna_score": r[6],
                        "created_at": r[7].isoformat() if r[7] else None,
                    }
                    for r in rows
                ]
        finally:
            conn.close()


db = Database(settings.database_url)
