"""Tests for arXiv ID normalization (offline tests only)."""

from marginalia.data.arxiv import ArxivClient


class TestArxivIDNormalization:
    def test_clean_id_passthrough(self):
        assert ArxivClient.normalize_arxiv_id("1706.03762") == "1706.03762"

    def test_strips_version(self):
        assert ArxivClient.normalize_arxiv_id("1706.03762v1") == "1706.03762"
        assert ArxivClient.normalize_arxiv_id("1706.03762v3") == "1706.03762"

    def test_extracts_from_url(self):
        assert ArxivClient.normalize_arxiv_id("https://arxiv.org/abs/1706.03762") == "1706.03762"
        assert ArxivClient.normalize_arxiv_id("arxiv.org/pdf/2310.06825") == "2310.06825"

    def test_handles_old_style_id(self):
        assert ArxivClient.normalize_arxiv_id("cs/0301001") == "cs/0301001"

    def test_strips_whitespace(self):
        assert ArxivClient.normalize_arxiv_id("  1706.03762  ") == "1706.03762"
