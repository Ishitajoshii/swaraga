"""Constrained decoding - the conformance guarantee (PRD section 7).

These are property tests, not examples. The claim "every output is in-raga and
of exact length" is the load-bearing claim of the whole architecture, so it is
checked across every model, every rung and many seeds rather than on one case.
"""

from __future__ import annotations

import random

import pandas as pd
import pytest

from swaraga import config
from swaraga.decode import ConstrainedDecoder, infer_direction
from swaraga.grammar import ASCENDING, DESCENDING, EITHER, RagaGrammarLibrary, TalaTemplate
from swaraga.models import BASELINES
from swaraga.windows import REST_DEGREE, build_windows

SEEDS = list(range(12))


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return pd.read_parquet(config.NORMALIZED_DATASET)


@pytest.fixture(scope="module")
def library() -> RagaGrammarLibrary:
    return RagaGrammarLibrary()


@pytest.fixture(scope="module")
def trained(frame, library):
    """Every baseline, fitted on all T2 windows."""
    windows = build_windows(frame, rung="T2", library=library)
    return {name: cls().fit(windows) for name, cls in BASELINES.items()}, windows


# --- the core guarantee -----------------------------------------------------

@pytest.mark.parametrize("model_name", sorted(BASELINES))
def test_output_is_always_in_raga(trained, frame, library, model_name) -> None:
    models, windows = trained
    model = models[model_name]
    by_id = {row["id"]: row for _, row in frame.iterrows()}

    for seed in SEEDS:
        window = windows[seed * 37 % len(windows)]
        grammar = library.for_row(by_id[window.record_id])
        decoder = ConstrainedDecoder(grammar, rng=random.Random(seed))
        result = decoder.decode(model, window.context_degrees, 8)

        for swara in result.swaras:
            if swara == config.REST:
                continue
            assert swara.rstrip("'.") in grammar.swaras, (
                f"{model_name} emitted {swara!r}, outside {grammar.raga}"
            )


@pytest.mark.parametrize("model_name", sorted(BASELINES))
@pytest.mark.parametrize("horizon", [1, 4, 8, 16, 32])
def test_output_length_is_exact(trained, frame, library, model_name, horizon) -> None:
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[0]
    grammar = library.for_row(by_id[window.record_id])
    decoder = ConstrainedDecoder(grammar, rng=random.Random(horizon))

    result = decoder.decode(models[model_name], window.context_degrees, horizon)
    assert len(result.degrees) == horizon
    assert len(result.swaras) == horizon


def test_guarantee_holds_across_every_rung(trained, frame, library) -> None:
    models, _ = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}

    for rung in ("T1", "T2", "T3"):
        windows = build_windows(frame, rung=rung, library=library)
        if not windows:
            continue
        for window in windows[:5]:
            grammar = library.for_row(by_id[window.record_id])
            decoder = ConstrainedDecoder(grammar, rng=random.Random(7))
            horizon = len(window.target_degrees)
            result = decoder.decode(models["B1"], window.context_degrees, horizon)
            assert len(result.degrees) == horizon
            for swara in result.swaras:
                if swara != config.REST:
                    assert swara.rstrip("'.") in grammar.swaras


def test_transitions_obey_the_grammar(trained, frame, library) -> None:
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[3]
    grammar = library.for_row(by_id[window.record_id])
    decoder = ConstrainedDecoder(grammar, rng=random.Random(1))

    result = decoder.decode(models["B1"], window.context_degrees, 12)
    history = [d for d in window.context_degrees if d != REST_DEGREE]
    for degree in result.degrees:
        if degree == REST_DEGREE:
            continue
        allowed = grammar.legal_next(grammar.from_degree(history[-1]))
        assert grammar.from_degree(degree) in allowed
        history.append(degree)


# --- decoder behaviour ------------------------------------------------------

def test_greedy_decoding_is_deterministic(trained, frame, library) -> None:
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[5]
    grammar = library.for_row(by_id[window.record_id])

    runs = [
        ConstrainedDecoder(grammar, rng=random.Random(seed))
        .decode(models["B1"], window.context_degrees, 8, greedy=True).degrees
        for seed in (1, 2, 3)
    ]
    assert runs[0] == runs[1] == runs[2]


def test_same_seed_reproduces_sampling(trained, frame, library) -> None:
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[5]
    grammar = library.for_row(by_id[window.record_id])

    first = ConstrainedDecoder(grammar, rng=random.Random(99)).decode(
        models["B1"], window.context_degrees, 8).degrees
    second = ConstrainedDecoder(grammar, rng=random.Random(99)).decode(
        models["B1"], window.context_degrees, 8).degrees
    assert first == second


def test_a_model_that_scores_nothing_still_produces_valid_output(
        trained, frame, library) -> None:
    """B0 returns no scores at all; the grammar must carry the decode."""
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[0]
    grammar = library.for_row(by_id[window.record_id])
    decoder = ConstrainedDecoder(grammar, rng=random.Random(4))

    result = decoder.decode(models["B0"], window.context_degrees, 8)
    assert len(result.degrees) == 8
    assert result.fell_back == 8


def test_rests_are_capped(trained, frame, library) -> None:
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[0]
    grammar = library.for_row(by_id[window.record_id])
    decoder = ConstrainedDecoder(grammar, rng=random.Random(2))

    result = decoder.decode(models["B0.5"], window.context_degrees, 40)
    run = best = 0
    for degree in result.degrees:
        run = run + 1 if degree == REST_DEGREE else 0
        best = max(best, run)
    assert best <= 3


def test_rests_can_be_disabled(trained, frame, library) -> None:
    models, windows = trained
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    window = windows[0]
    grammar = library.for_row(by_id[window.record_id])
    decoder = ConstrainedDecoder(grammar, rng=random.Random(2), allow_rests=False)

    result = decoder.decode(models["B1"], window.context_degrees, 16)
    assert REST_DEGREE not in result.degrees


# --- direction --------------------------------------------------------------

def test_direction_inference() -> None:
    assert infer_direction([0, 1, 2, 3]) == ASCENDING
    assert infer_direction([4, 3, 2, 1]) == DESCENDING
    assert infer_direction([2, 2, 2]) == EITHER
    assert infer_direction([]) == EITHER


def test_direction_ignores_rests() -> None:
    assert infer_direction([0, REST_DEGREE, 1, REST_DEGREE, 2]) == ASCENDING


def test_optional_repeat_limit_includes_seed_and_preserves_legal_motion(library):
    class RepeatOnly:
        def next_scores(self, context):
            return {context[-1]: 1.0}

    grammar = library.get("Mohanam", 28)
    baseline = ConstrainedDecoder(grammar, allow_rests=False)
    assert baseline.decode(RepeatOnly(), [0, 0], 4).degrees == [0, 0, 0, 0]
    decoder = ConstrainedDecoder(grammar, allow_rests=False, max_consecutive_notes=2)
    result = decoder.decode(RepeatOnly(), [0, 0], 20)
    history = [0, 0]
    for degree in result.degrees:
        assert degree in decoder.legal_degrees(history)
        assert history[-2:] != [degree, degree]
        history.append(degree)


def test_repeat_preference_does_not_force_an_illegal_note(library, monkeypatch):
    class RepeatOnly:
        def next_scores(self, context):
            return {0: 1.0}

    decoder = ConstrainedDecoder(library.get("Mohanam", 28), allow_rests=False,
                                 max_consecutive_notes=2)
    monkeypatch.setattr(decoder, "legal_degrees", lambda context: {0})
    assert decoder.decode(RepeatOnly(), [0, 0], 4).degrees == [0, 0, 0, 0]
