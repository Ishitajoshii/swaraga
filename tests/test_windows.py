"""Windowing and scale-degree encoding (PRD sections 3, 4)."""

from __future__ import annotations

import pandas as pd
import pytest

from swaraga import config
from swaraga.grammar import RagaGrammarLibrary
from swaraga.windows import (
    DEFAULT_RUNG,
    FOREIGN_DEGREE,
    REST_DEGREE,
    RUNGS,
    build_windows,
    from_degrees,
    is_note,
    split_windows,
    to_degrees,
    window_counts,
)


@pytest.fixture(scope="module")
def frame() -> pd.DataFrame:
    return pd.read_parquet(config.NORMALIZED_DATASET)


@pytest.fixture(scope="module")
def library() -> RagaGrammarLibrary:
    return RagaGrammarLibrary()


def test_v1_target_is_t2() -> None:
    assert DEFAULT_RUNG == "T2"


@pytest.mark.parametrize("rung,context,horizon", [("T1", 12, 4), ("T2", 16, 8)])
def test_window_shapes(frame, library, rung, context, horizon) -> None:
    windows = build_windows(frame, rung=rung, library=library)
    assert windows
    for window in windows:
        assert len(window.context) == context
        assert len(window.target) == horizon
        assert len(window.context_degrees) == context
        assert len(window.target_degrees) == horizon


def test_windows_never_cross_compositions(frame, library) -> None:
    """Each window must come from exactly one piece."""
    by_id = {row["id"]: list(row["swara_sequence"]) for _, row in frame.iterrows()}
    for window in build_windows(frame, rung="T2", library=library):
        source = by_id[window.record_id]
        span = window.context + window.target
        start = window.start
        assert source[start:start + len(span)] == span


def test_shorter_horizon_yields_more_windows(frame, library) -> None:
    """The whole reason the ladder exists (PRD section 3)."""
    counts = window_counts(frame, library)
    assert counts["T1"]["total"] > counts["T2"]["total"] > counts["T3"]["total"]


def test_t3_is_starved_on_current_data(frame, library) -> None:
    """Documents why T3 is not the v1 target."""
    counts = window_counts(frame, library)
    assert counts["T3"]["compositions_contributing"] < 10
    assert counts["T3"]["ragas_covered"] < counts["T2"]["ragas_covered"]


def test_free_alapana_yields_no_avartana_windows(frame, library) -> None:
    """Unmetered material has no avartana, so T3 cannot apply to it."""
    unmetered = frame.loc[~frame["is_metered"], "id"].tolist()
    assert unmetered
    ids = {w.record_id for w in build_windows(frame, rung="T3", library=library)}
    assert not (ids & set(unmetered))


# --- degree encoding --------------------------------------------------------

def test_degree_round_trip_on_every_clean_composition(frame, library) -> None:
    """Round-trip is identity wherever the notation is actually in its raga."""
    checked = 0
    for _, row in frame.iterrows():
        grammar = library.for_row(row)
        sequence = list(row["swara_sequence"])
        degrees = to_degrees(sequence, grammar)
        if FOREIGN_DEGREE in degrees:
            continue                      # covered by the test below
        assert from_degrees(degrees, grammar) == sequence
        checked += 1
    assert checked >= len(frame) - 1


def test_out_of_raga_notes_are_flagged_not_silently_rested(frame, library) -> None:
    """`hindolam_keerthanam_001` has a rishabha; Hindolam has none.

    A foreign swara must land on FOREIGN_DEGREE. Folding it into REST_DEGREE
    would quietly convert a data error into silence and hide it from the
    quality log.
    """
    row = frame.loc[frame["id"] == "hindolam_keerthanam_001"].iloc[0]
    degrees = to_degrees(list(row["swara_sequence"]), library.for_row(row))
    assert FOREIGN_DEGREE in degrees
    assert not is_note(FOREIGN_DEGREE)


def test_rest_and_foreign_markers_never_collide_with_real_degrees() -> None:
    """The bug this guards: REST_DEGREE used to be -1, the note below Sa."""
    for marker in (REST_DEGREE, FOREIGN_DEGREE):
        assert marker < -100, "marker must sit far outside any register"
        assert not is_note(marker)
    assert is_note(-1) and is_note(0) and is_note(13)


def test_rests_survive_degree_encoding(frame, library) -> None:
    row = frame.iloc[0]
    grammar = library.for_row(row)
    degrees = to_degrees(list(row["swara_sequence"]), grammar)
    n_rests = list(row["swara_sequence"]).count(config.REST)
    assert degrees.count(REST_DEGREE) == n_rests


def test_octave_is_carried_into_the_degree(library) -> None:
    """S and S' must stay distinguishable, or contour breaks at the octave."""
    grammar = library.get("Mohanam", 28)
    assert to_degrees(["S"], grammar) == [0]
    assert to_degrees(["S'"], grammar) == [5]
    assert to_degrees(["S."], grammar) == [-5]


def test_contour_transfers_across_ragas(library) -> None:
    """The mechanism that makes pooling work (PRD section 4)."""
    mohanam = library.get("Mohanam", 28)       # S R2 G3 P  D2
    hindolam = library.get("Hindolam", 20)     # S G2 M1 D1 N2
    assert to_degrees(["S", "R2", "G3", "P", "D2"], mohanam) == [0, 1, 2, 3, 4]
    assert to_degrees(["S", "G2", "M1", "D1", "N2"], hindolam) == [0, 1, 2, 3, 4]


def test_degrees_reinstantiate_into_the_target_raga(library) -> None:
    """A contour learned anywhere can be emitted in a specific raga."""
    hindolam = library.get("Hindolam", 20)
    assert from_degrees([0, 1, 2, 3, 4], hindolam) == ["S", "G2", "M1", "D1", "N2"]


# --- leakage ----------------------------------------------------------------

def test_split_assigns_by_composition_not_window(frame, library) -> None:
    """Overlapping windows must never straddle a split boundary."""
    windows = build_windows(frame, rung="T2", library=library)
    ids = sorted({w.record_id for w in windows})
    splits = {"train": ids[:-4], "val": ids[-4:-2], "test": ids[-2:]}

    parts = split_windows(windows, splits)
    seen: dict[str, str] = {}
    for name, part in parts.items():
        for window in part:
            assert seen.setdefault(window.record_id, name) == name


def test_every_window_is_assigned(frame, library) -> None:
    windows = build_windows(frame, rung="T2", library=library)
    ids = sorted({w.record_id for w in windows})
    splits = {"train": ids[:-4], "val": ids[-4:-2], "test": ids[-2:]}
    parts = split_windows(windows, splits)
    assert sum(len(p) for p in parts.values()) == len(windows)


def test_unknown_rung_is_rejected(frame) -> None:
    with pytest.raises(ValueError):
        build_windows(frame, rung="T9")


def test_rung_registry_is_complete() -> None:
    for spec in RUNGS.values():
        assert {"context", "horizon", "unit", "label"} <= set(spec)
