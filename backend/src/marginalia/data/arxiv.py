"""
arXiv API client with cache.

Fetches paper metadata and PDFs from arXiv.
Respects strict 1 req/3sec rate limit.
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import httpx

from marginalia.data.cache import cache
from marginalia.data.pdf import PaperSections, extract_sections_from_pdf

logger = logging.getLogger(__name__)


@dataclass
class ArxivPaper:
    arxiv_id: str
    title: str
    abstract: str
    sections: PaperSections


class ArxivClient:
    """Async client for arXiv API + PDF download with caching."""

    BASE_URL = "https://export.arxiv.org/api/query"
    PDF_URL = "https://arxiv.org/pdf/{}"

    def __init__(self, cache_dir: str | Path = ".arxiv_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request: float = 0.0
        self._lock = asyncio.Lock()

    @staticmethod
    def normalize_arxiv_id(value: str) -> str:
        """Extract clean arXiv ID from URL or raw ID."""
        value = value.strip()
        match = re.search(r"(\d{4}\.\d{4,5}|[a-z\-]+/\d{7})(v\d+)?", value)
        if match:
            return match.group(1)
        return value

    async def _rate_limit(self) -> None:
        """Enforce 1 req / 3 sec arXiv rate limit."""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            wait = 3.0 - (now - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = asyncio.get_event_loop().time()

    async def fetch_metadata(self, arxiv_id: str) -> dict:
        """Fetch paper metadata from arXiv API."""
        clean_id = self.normalize_arxiv_id(arxiv_id)

        # Try cache first
        cache_key = f"arxiv:meta:{clean_id}"
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"arXiv metadata cache hit: {clean_id}")
            return cached

        await self._rate_limit()

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                self.BASE_URL,
                params={"id_list": clean_id, "max_results": 1},
            )
            response.raise_for_status()
            xml = response.text

        all_titles = re.findall(r"<title>(.*?)</title>", xml, re.DOTALL)
        title = all_titles[1].strip() if len(all_titles) > 1 else "Unknown"

        summary_match = re.search(r"<summary>(.*?)</summary>", xml, re.DOTALL)
        abstract = summary_match.group(1).strip() if summary_match else ""

        result = {"title": title, "abstract": abstract, "arxiv_id": clean_id}
        await cache.set(cache_key, result, ttl_seconds=7 * 86400)  # 7 days
        return result

    async def fetch_pdf(self, arxiv_id: str) -> Path:
        """Download (or cache) a paper PDF. Returns local path."""
        clean_id = self.normalize_arxiv_id(arxiv_id)
        safe_id = clean_id.replace("/", "_")
        cache_path = self.cache_dir / f"{safe_id}.pdf"

        if cache_path.exists() and cache_path.stat().st_size > 1000:
            logger.info(f"arXiv PDF disk cache hit: {clean_id}")
            return cache_path

        await self._rate_limit()
        url = self.PDF_URL.format(clean_id)
        logger.info(f"Downloading arXiv PDF: {url}")

        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            cache_path.write_bytes(response.content)

        return cache_path

    async def fetch_paper(self, arxiv_id: str) -> ArxivPaper:
        """Fetch metadata + PDF + extracted sections, with full caching."""
        clean_id = self.normalize_arxiv_id(arxiv_id)

        # Try cached parsed paper
        cache_key = f"arxiv:paper:{clean_id}"
        cached = await cache.get(cache_key)
        if cached:
            logger.info(f"arXiv paper cache hit: {clean_id}")
            return ArxivPaper(
                arxiv_id=cached["arxiv_id"],
                title=cached["title"],
                abstract=cached["abstract"],
                sections=PaperSections(**cached["sections"]),
            )

        meta = await self.fetch_metadata(clean_id)
        pdf_path = await self.fetch_pdf(meta["arxiv_id"])
        sections = extract_sections_from_pdf(pdf_path)

        if not sections.abstract.strip() and meta["abstract"]:
            sections.abstract = meta["abstract"]

        paper = ArxivPaper(
            arxiv_id=meta["arxiv_id"],
            title=meta["title"],
            abstract=sections.abstract or meta["abstract"],
            sections=sections,
        )

        # Cache parsed result
        await cache.set(
            cache_key,
            {
                "arxiv_id": paper.arxiv_id,
                "title": paper.title,
                "abstract": paper.abstract,
                "sections": asdict(paper.sections),
            },
            ttl_seconds=7 * 86400,
        )
        return paper


arxiv_client = ArxivClient()
