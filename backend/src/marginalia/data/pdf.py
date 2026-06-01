"""
PDF Parser — Extracts structured sections from academic paper PDFs.

Uses PyMuPDF (fitz) as primary parser.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PaperSections:
    full_text: str
    abstract: str = ""
    introduction: str = ""
    methodology: str = ""
    results: str = ""
    conclusion: str = ""
    references_raw: str = ""
    figure_count: int = 0
    table_count: int = 0
    equation_count: int = 0

    def body_dict(self) -> dict[str, str]:
        """Return body sections as dict (excluding abstract and refs)."""
        return {
            "introduction": self.introduction,
            "methodology": self.methodology,
            "results": self.results,
            "conclusion": self.conclusion,
        }


def extract_sections_from_pdf(pdf_path: str | Path) -> PaperSections:
    """Extract structured sections from a PDF file."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("PyMuPDF not installed — install with: pip install pymupdf")
        return PaperSections(full_text="")

    try:
        doc = fitz.open(str(pdf_path))
        full_text = "\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        logger.error(f"PDF parse error: {e}")
        return PaperSections(full_text="")

    return extract_sections_from_text(full_text)


def extract_sections_from_text(full_text: str) -> PaperSections:
    """Extract sections from already-extracted text."""
    sections = PaperSections(full_text=full_text)
    sections.abstract = _extract_between(
        full_text, r"\babstract\b", r"(\b1\.?\s*introduction\b|\bintroduction\b)"
    )
    sections.introduction = _extract_between(
        full_text,
        r"(\b1\.?\s*introduction\b|\bintroduction\b)",
        r"(\b2\.?\s|\brelated work\b|\bbackground\b)",
    )
    sections.methodology = _extract_between(
        full_text,
        r"(\bmethod\b|\bapproach\b|\bmethodology\b|\b3\.?\s)",
        r"(\bexperiment\b|\bresult\b|\bevaluation\b|\b4\.?\s)",
    )
    sections.results = _extract_between(
        full_text,
        r"(\bexperiment\b|\bresult\b|\bevaluation\b)",
        r"(\bdiscussion\b|\bconclusion\b|\b6\.?\s)",
    )
    sections.conclusion = _extract_between(
        full_text,
        r"(\bconclusion\b|\bdiscussion\b)",
        r"(\breference\b|\bbibliography\b|\backnowledge\b)",
    )
    sections.references_raw = _extract_between(
        full_text, r"(\breference\b|\bbibliography\b)", r"$"
    )

    # Count structural elements
    sections.figure_count = len(
        re.findall(r"\bfig(?:ure)?\.?\s*\d+", full_text, re.IGNORECASE)
    )
    sections.table_count = len(re.findall(r"\btable\s*\d+", full_text, re.IGNORECASE))
    sections.equation_count = len(
        re.findall(r"\beq(?:uation)?\.?\s*[\(\[]?\d+", full_text, re.IGNORECASE)
    )

    return sections


def _extract_between(text: str, start_pattern: str, end_pattern: str) -> str:
    """Extract text between two regex patterns, capped at 5000 chars."""
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    if not start_match:
        return ""

    end_match = re.search(end_pattern, text[start_match.end():], re.IGNORECASE)
    if not end_match:
        return text[start_match.end():start_match.end() + 5000].strip()

    end_pos = start_match.end() + end_match.start()
    chunk = text[start_match.end():end_pos].strip()
    return chunk[:5000]  # cap to avoid embedding huge sections
