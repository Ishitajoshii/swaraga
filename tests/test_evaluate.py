"""The metric suite (PRD section 9).

The most important test here is
:func:`test_ground_truth_novelty_is_low`, which pins the control that stops
`novelty` being read the wrong way round.
"""

from __future__ import annotations

import pandas as pd
import pytest

from swaraga import config
from swaraga.evaluate import (
    ContinuationResult,
    contour_distance,
    evaluate,
    exact_match,
    novelty,
    nyasa_appropriateness,
    perplexity,
    raga_conformance,
    reference_results,
    training_ngram_set,
)
from swaraga.grammar import RagaGrammarLibrary
from swaraga.models import VariableOrderMarkov
from swaraga.windows import REST_DEGREE, build_windows, is_note


@pytest.fixture(scope="module")
def setup():
    frame = pd.read_parquet(config.NORMALIZED_DATASET)
    library = RagaGrammarLibrary()
    windows = build_windows(frame, rung="T2", library=library)
    grammars = {row["id"]: library.for_row(row) for _, row in frame.iterrows()}
    return frame, library, windows, grammars


def result_for(window, grammar, generated):
    return ContinuationResult(window=window, generated=list(generated),
                              grammar=grammar)


# --- the control ------------------------------------------------------------

def test_ground_truth_novelty_is_low(setup) -> None:
    """Real human continuations reuse ~87% of their 4-grams.

    This is why `novelty` must be read against the GT reference row and never
    against 1.00: in a 15-symbol degree vocabulary over formulaic repertoire,
    heavy n-gram reuse is normal music, not memorisation.
    """
    _, _, windows, grammars = setup
    train, test = windows[:400], windows[400:]
    grams = training_ngram_set(train)
    scores = [novelty(r, grams) for r in reference_results(test, grammars)]
    mean = sum(scores) / len(scores)
    assert 0.0 < mean < 0.4, f"ground-truth novelty {mean:.2f} outside expected band"


def test_ground_truth_scores_perfectly_on_similarity(setup) -> None:
    _, _, windows, grammars = setup
    results = reference_results(windows[:20], grammars)
    assert all(contour_distance(r) == 0.0 for r in results)
    assert all(exact_match(r) == 1.0 for r in results)


# --- contract checks --------------------------------------------------------

def test_conformance_is_perfect_for_in_raga_output(setup) -> None:
    _, library, windows, _ = setup
    grammar = library.get("Mohanam", 28)
    assert raga_conformance(result_for(windows[0], grammar, [0, 1, 2, 3])) == 1.0


def test_conformance_ignores_rests(setup) -> None:
    _, library, windows, _ = setup
    grammar = library.get("Mohanam", 28)
    assert raga_conformance(
        result_for(windows[0], grammar, [REST_DEGREE, REST_DEGREE])) == 1.0


# --- results ----------------------------------------------------------------

def test_contour_distance_rewards_matching_shape(setup) -> None:
    """A right shape in the wrong register beats a wrong shape in the right one."""
    _, library, windows, _ = setup
    grammar = library.get("Mohanam", 28)
    window = windows[0]
    truth = list(window.target_degrees)

    transposed = result_for(window, grammar,
                            [d + 1 if is_note(d) else d for d in truth])
    scrambled = result_for(window, grammar, list(reversed(truth)))
    assert contour_distance(transposed) < contour_distance(scrambled)


def test_nyasa_detects_a_resting_ending(setup) -> None:
    _, library, windows, _ = setup
    grammar = library.get("Hamsadhwani", 29)     # nyasa: S R G P, not N
    ends_on_sa = result_for(windows[0], grammar, [2, 1, 0])
    ends_on_ni = result_for(windows[0], grammar, [2, 3, 4])
    assert nyasa_appropriateness(ends_on_sa) == 1.0
    assert nyasa_appropriateness(ends_on_ni) == 0.0


def test_novelty_detects_verbatim_copying(setup) -> None:
    _, library, windows, _ = setup
    grammar = library.get("Mohanam", 28)
    grams = training_ngram_set(windows[:50])
    copied = list(windows[0].context_degrees) + list(windows[0].target_degrees)
    assert novelty(result_for(windows[0], grammar, copied), grams) == 0.0


def test_novelty_is_one_for_unseen_material(setup) -> None:
    _, library, windows, _ = setup
    grammar = library.get("Mohanam", 28)
    grams = training_ngram_set(windows[:50])
    assert novelty(result_for(windows[0], grammar, [77, 78, 79, 80]), grams) == 1.0


def test_perplexity_is_finite_for_a_distribution_model(setup) -> None:
    _, _, windows, _ = setup
    model = VariableOrderMarkov().fit(windows[:400])
    value = perplexity(model, windows[400:])
    assert value is not None and value > 0


def test_perplexity_is_none_without_a_distribution(setup) -> None:
    """Models with no distribution get a blank cell, not an invented number."""
    _, _, windows, _ = setup

    class NoDistribution:
        def next_scores(self, context):
            return {}

    assert perplexity(NoDistribution(), windows[:10]) is None


# --- aggregation ------------------------------------------------------------

def test_report_carries_every_metric(setup) -> None:
    _, _, windows, grammars = setup
    grams = training_ngram_set(windows[:400])
    report = evaluate(reference_results(windows[400:420], grammars),
                      "GT", "T2", grams)
    assert report.n_windows == 20
    for key in ("raga_conformance", "transition_legality", "length_exact",
                "nyasa", "contour_distance", "exact_match", "novelty"):
        assert key in report.metrics


def test_empty_evaluation_is_safe() -> None:
    report = evaluate([], "B0", "T2", set())
    assert report.n_windows == 0


def test_dtw_is_banded_not_degenerate() -> None:
    """Unconstrained DTW scored opposite contours as identical.

    It could stretch one symbol to cover many, so an ascent and a descent
    aligned at zero cost. Since `contour_distance` is the primary ranking
    metric, that silently invalidated every model comparison.
    """
    from swaraga.evaluate import _dtw

    ascent = [1, 1, 1, 1, 1, -1]
    descent = [1, -1, -1, -1, -1, -1]
    assert _dtw(ascent, descent) > 0.0
    assert _dtw(ascent, ascent) == 0.0


def test_contour_distance_is_zero_under_transposition(setup) -> None:
    """Same shape, different register - intervals are unchanged."""
    _, library, windows, _ = setup
    grammar = library.get("Mohanam", 28)
    window = windows[0]
    truth = list(window.target_degrees)
    shifted = [d + 1 if is_note(d) else d for d in truth]
    assert contour_distance(result_for(window, grammar, shifted)) == 0.0
