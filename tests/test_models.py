"""The four v1 baselines (PRD section 8)."""

from __future__ import annotations

import pandas as pd
import pytest

from swaraga import config
from swaraga.grammar import RagaGrammarLibrary
from swaraga.models import (
    BASELINES,
    DirectionHeuristic,
    GrammarRandomWalk,
    RetrievalModel,
    VariableOrderMarkov,
)
from swaraga.windows import REST_DEGREE, build_windows


@pytest.fixture(scope="module")
def windows():
    frame = pd.read_parquet(config.NORMALIZED_DATASET)
    return build_windows(frame, rung="T2", library=RagaGrammarLibrary())


def test_roadmap_is_complete() -> None:
    assert sorted(BASELINES) == ["B0", "B0.5", "B1", "B2"]


@pytest.mark.parametrize("name", sorted(BASELINES))
def test_every_baseline_shares_one_interface(windows, name) -> None:
    model = BASELINES[name]().fit(windows)
    scores = model.next_scores(windows[0].context_degrees)
    assert isinstance(scores, dict)
    assert all(isinstance(k, int) for k in scores)


# --- B0 ---------------------------------------------------------------------

def test_random_walk_contributes_nothing(windows) -> None:
    """B0 is the floor: the constraint does all the work."""
    assert GrammarRandomWalk().fit(windows).next_scores([0, 1, 2]) == {}


# --- B0.5 -------------------------------------------------------------------

def test_heuristic_continues_an_ascent() -> None:
    scores = DirectionHeuristic().fit([]).next_scores([0, 1, 2])
    assert scores[3] > scores[1], "should prefer continuing up over turning back"


def test_heuristic_continues_a_descent() -> None:
    scores = DirectionHeuristic().fit([]).next_scores([4, 3, 2])
    assert scores[1] > scores[3]


def test_heuristic_prefers_small_steps() -> None:
    scores = DirectionHeuristic().fit([]).next_scores([0, 1, 2])
    assert scores[3] > scores[4] > scores[5]


def test_heuristic_is_symmetric_without_a_direction() -> None:
    scores = DirectionHeuristic().fit([]).next_scores([2, 2])
    assert scores[3] == scores[1]


def test_heuristic_needs_no_data() -> None:
    """The prior is the whole model - it must work with an empty training set."""
    assert DirectionHeuristic().fit([]).next_scores([0, 1])


# --- B1 ---------------------------------------------------------------------

def test_markov_learns_from_data(windows) -> None:
    model = VariableOrderMarkov().fit(windows)
    assert model.n_observations > 0
    assert model.next_scores(windows[0].context_degrees)


def test_markov_probabilities_are_normalised(windows) -> None:
    model = VariableOrderMarkov().fit(windows)
    context = windows[0].context_degrees
    scores = model.next_scores(context)
    total = sum(model.probability(context, d) for d in scores)
    assert total == pytest.approx(1.0, abs=1e-9)


def test_markov_backs_off_to_shorter_contexts(windows) -> None:
    """An unseen long context must still yield a distribution."""
    model = VariableOrderMarkov().fit(windows)
    assert model.next_scores([99, 98, 97, 0])


def test_markov_prefers_what_it_saw() -> None:
    model = VariableOrderMarkov(max_order=3)
    model._count_sequence([0, 1, 2, 3] * 10)
    scores = model.next_scores([0, 1, 2])
    assert max(scores, key=scores.get) == 3


def test_untrained_markov_returns_nothing() -> None:
    assert VariableOrderMarkov().next_scores([0, 1, 2]) == {}


# --- B2 ---------------------------------------------------------------------

def test_retrieval_indexes_windows(windows) -> None:
    model = RetrievalModel().fit(windows)
    assert len(model.entries) > 0
    assert model.next_scores(windows[0].context_degrees)


def test_retrieval_matches_on_interval_shape() -> None:
    """Contour, not absolute pitch, is what transfers across ragas."""
    model = RetrievalModel(contour_length=4)
    assert model._contour([0, 1, 2, 3]) == model._contour([5, 6, 7, 8])


def test_retrieval_reanchors_to_the_query_register(windows) -> None:
    """The bug this guards: proposals must not collapse onto the anchor note."""
    model = RetrievalModel().fit(windows)
    low = model.next_scores([0, 1, 2, 3])
    high = model.next_scores([5, 6, 7, 8])
    assert low and high
    assert max(high, key=high.get) > max(low, key=low.get)


def test_retrieval_with_no_index_returns_nothing() -> None:
    assert RetrievalModel().fit([]).next_scores([0, 1, 2]) == {}


def test_retrieval_handles_rest_only_context() -> None:
    model = RetrievalModel()
    assert model._contour([REST_DEGREE, REST_DEGREE]) == ()
