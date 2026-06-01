"""Tests for Ghost Score aggregator."""

from marginalia.engines.aggregator import compute_ghost_score
from marginalia.engines.asymmetry import AsymmetryResult
from marginalia.engines.batch_dna import BatchDNAResult
from marginalia.engines.specificity import score_specificity


def _make_asym(score: float = 0.0) -> AsymmetryResult:
    return AsymmetryResult(
        score=score,
        sim_abstract=0.5,
        sim_body=0.5,
        asymmetry_ratio=0.5,
        hallucinated_sentences=[],
    )


def _make_batch(score: float | None = None, available: bool = False, size: int = 1) -> BatchDNAResult:
    return BatchDNAResult(
        score=score,
        cluster_id=0,
        cluster_size=size,
        available=available,
        reason=None,
    )


class TestAggregator:
    def test_high_specificity_yields_low_ghost(self):
        spec = score_specificity(
            "Equation 5 in Section 3.2 has a sign error. Figure 4 shows the issue. "
            "Table 2 confirms the mismatch."
        )
        result = compute_ghost_score(
            specificity=spec,
            asymmetry=_make_asym(),
            batch_dna=None,
            review_word_count=300,
        )
        assert result.overall < 50

    def test_low_specificity_yields_high_ghost(self):
        spec = score_specificity(
            "This paper is interesting. The methodology is clear. "
            "The results are promising. I recommend acceptance."
        )
        result = compute_ghost_score(
            specificity=spec,
            asymmetry=_make_asym(),
            batch_dna=None,
            review_word_count=300,
        )
        assert result.overall > 50

    def test_score_in_valid_range(self):
        spec = score_specificity("Some review text here with words.")
        result = compute_ghost_score(
            specificity=spec,
            asymmetry=_make_asym(85.0),
            batch_dna=_make_batch(80.0, available=True, size=3),
            review_word_count=300,
        )
        assert 0 <= result.overall <= 100

    def test_confidence_interval_wider_for_short_reviews(self):
        spec = score_specificity("Short review.")
        long_spec = score_specificity(" ".join(["word"] * 500))

        short = compute_ghost_score(spec, _make_asym(), None, 50)
        long_r = compute_ghost_score(long_spec, _make_asym(), None, 500)

        short_width = short.confidence_high - short.confidence_low
        long_width = long_r.confidence_high - long_r.confidence_low
        assert short_width > long_width

    def test_explanation_is_string(self):
        spec = score_specificity("Equation 3 is wrong.")
        result = compute_ghost_score(spec, _make_asym(), None, 100)
        assert isinstance(result.explanation, str)
        assert len(result.explanation) > 0

    def test_label_assigned(self):
        spec = score_specificity("Bad review.")
        result = compute_ghost_score(spec, _make_asym(), None, 100)
        assert result.label in [
            "likely human",
            "uncertain — lean human",
            "uncertain — lean AI",
            "likely AI-generated",
            "almost certainly AI-generated",
        ]

    def test_with_all_three_layers(self):
        spec = score_specificity("This is a generic review without specifics.")
        asym = _make_asym(80.0)
        batch = _make_batch(75.0, available=True, size=4)
        result = compute_ghost_score(spec, asym, batch, 300)
        # All layers high → high overall
        assert result.overall > 60
        assert result.batch_dna.available
