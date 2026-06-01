"""Tests for PDF section extraction."""

from marginalia.data.pdf import extract_sections_from_text


SAMPLE_PAPER_TEXT = """
Title of the Paper

Abstract
This paper presents a novel approach to attention mechanisms in transformer models.
We propose a new method that achieves state-of-the-art results on multiple benchmarks.

1. Introduction
The transformer architecture has revolutionized natural language processing.
However, attention computation remains expensive.

2. Related Work
Prior work on efficient attention includes Linformer and Performer.

3. Method
Our methodology consists of three key components.
First, we introduce sparse attention patterns.
Equation 1: A = softmax(QK^T / sqrt(d_k))
See Figure 2 for details.

4. Experiments
We evaluate on GLUE and SuperGLUE benchmarks.
Table 1 shows our main results.

5. Discussion
Our approach demonstrates significant improvements.

6. Conclusion
We presented a new attention mechanism.

References
[1] Vaswani et al., Attention Is All You Need, 2017.
"""


class TestPDFExtraction:
    def test_extracts_abstract(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        assert "novel approach" in sections.abstract.lower()

    def test_extracts_introduction(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        assert "transformer architecture" in sections.introduction.lower()

    def test_extracts_methodology(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        # Methodology section should contain method details
        assert sections.methodology  # non-empty

    def test_counts_figures(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        assert sections.figure_count >= 1

    def test_counts_tables(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        assert sections.table_count >= 1

    def test_counts_equations(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        assert sections.equation_count >= 1

    def test_body_dict_excludes_abstract_and_refs(self):
        sections = extract_sections_from_text(SAMPLE_PAPER_TEXT)
        body = sections.body_dict()
        assert "abstract" not in body
        assert "references" not in body
        assert "introduction" in body

    def test_handles_empty_text(self):
        sections = extract_sections_from_text("")
        assert sections.full_text == ""
        assert sections.abstract == ""
