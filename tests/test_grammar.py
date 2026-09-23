"""Raga grammar and tala templates - the hard constraints."""

from __future__ import annotations

import pytest

from swaraga.grammar import (
    ASCENDING,
    DESCENDING,
    GrammarError,
    RagaGrammar,
    RagaGrammarLibrary,
    TalaTemplate,
)

#: The five v1 target ragas and their scales, as an independent check that the
#: curated config plus melakarta resolution agree with known musicology.
TARGET_RAGAS = [
    ("Mohanam", 28, ["S", "R2", "G3", "P", "D2"]),
    ("Hamsadhwani", 29, ["S", "R2", "G3", "P", "N3"]),
    ("Hindolam", 20, ["S", "G2", "M1", "D1", "N2"]),
    ("Abhogi", 22, ["S", "R2", "G2", "M1", "D2"]),
    ("Suddha Saveri", 29, ["S", "R2", "M1", "P", "D2"]),
]


@pytest.fixture(scope="module")
def library() -> RagaGrammarLibrary:
    return RagaGrammarLibrary()


@pytest.mark.parametrize("raga,mela,scale", TARGET_RAGAS)
def test_target_raga_scales(library, raga, mela, scale) -> None:
    grammar = library.get(raga, mela)
    assert grammar.scale == scale


def test_all_five_target_ragas_are_curated(library) -> None:
    assert library.curated_ragas == [
        "Abhogi", "Hamsadhwani", "Hindolam", "Mohanam", "Suddha Saveri",
    ]


@pytest.mark.parametrize("raga,mela,scale", TARGET_RAGAS)
def test_target_ragas_are_pentatonic(library, raga, mela, scale) -> None:
    """PRD section 5 picks these because the state space is small."""
    assert len(scale) == 5
    assert library.get(raga, mela).n_degrees == 5


def test_varjya_swaras_are_absent(library) -> None:
    """Hindolam has no rishabha and no panchama - the whole point of the raga."""
    grammar = library.get("Hindolam", 20)
    assert not any(s.startswith("R") for s in grammar.swaras)
    assert "P" not in grammar.swaras


def test_hindolam_rejects_the_rishabha_the_corpus_contains(library) -> None:
    """`hindolam_keerthanam_001` has an `R`; the grammar must not accept it."""
    grammar = library.get("Hindolam", 20)
    assert not grammar.is_legal("R2")


def test_direction_changes_what_is_legal(library) -> None:
    """A raga's asymmetry is most of what makes it recognisable."""
    # Sahana-like vakra is absent from the pentatonic set, so use a raga whose
    # arohanam and avarohanam differ in reachability from a given note.
    grammar = library.get("Mohanam", 28)
    up = grammar.legal_next("G3", ASCENDING)
    down = grammar.legal_next("G3", DESCENDING)
    assert up != down
    assert "P" in up            # G -> P ascends
    assert "R2" in down         # G -> R descends


def test_legal_next_allows_skips(library) -> None:
    """Carnatic phrases skip notes freely (S G P), so adjacency is too strict."""
    grammar = library.get("Mohanam", 28)
    assert "P" in grammar.legal_next("S", ASCENDING)


def test_legal_next_never_leaves_the_raga(library) -> None:
    for raga, mela, _ in TARGET_RAGAS:
        grammar = library.get(raga, mela)
        for swara in grammar.swaras:
            assert grammar.legal_next(swara) <= grammar.swaras


def test_phrase_start_uses_graha(library) -> None:
    grammar = library.get("Abhogi", 22)
    assert grammar.legal_next(None) == grammar.graha


def test_out_of_raga_input_does_not_deadlock(library) -> None:
    """A bad context must not leave the decoder with no legal move."""
    grammar = library.get("Hindolam", 20)
    assert grammar.legal_next("R2") == grammar.swaras


# --- scale degrees ----------------------------------------------------------

@pytest.mark.parametrize("raga,mela,scale", TARGET_RAGAS)
def test_degree_round_trip(library, raga, mela, scale) -> None:
    grammar = library.get(raga, mela)
    for index, swara in enumerate(scale):
        assert grammar.to_degree(swara) == index
        assert grammar.from_degree(index) == swara


def test_degrees_wrap_across_octaves(library) -> None:
    """Degree 5 in a pentatonic raga is the octave above degree 0."""
    grammar = library.get("Mohanam", 28)
    assert grammar.from_degree(5) == grammar.from_degree(0)
    assert grammar.degree_octave(5) == 1
    assert grammar.degree_octave(2) == 0


def test_foreign_swara_has_no_degree(library) -> None:
    assert library.get("Hindolam", 20).to_degree("R2") is None


# --- uncurated ragas --------------------------------------------------------

def test_uncurated_raga_falls_back_to_supplied_scales(library) -> None:
    """Ragas outside the v1 five still get a usable grammar from the dataset."""
    grammar = library.get("Kalyani", 65,
                          arohanam=["S", "R2", "G3", "M2", "P", "D2", "N3"],
                          avarohanam=["N3", "D2", "P", "M2", "G3", "R2", "S"])
    assert grammar.n_degrees == 7
    assert "M2" in grammar.swaras


def test_uncurated_raga_without_scales_is_an_error(library) -> None:
    with pytest.raises(GrammarError):
        library.get("Some Unlisted Raga", 29)


def test_from_scales_requires_both_directions() -> None:
    with pytest.raises(GrammarError):
        RagaGrammar.from_scales("X", 29, [], [])


# --- tala -------------------------------------------------------------------

def test_avartana_length() -> None:
    template = TalaTemplate("Adi", aksharas=8, kala=2)
    assert template.positions_per_avartana == 16
    assert template.positions_for(2) == 32


def test_strong_beats_fall_on_aksharas() -> None:
    template = TalaTemplate("Adi", aksharas=8, kala=2)
    assert template.is_strong_beat(0)
    assert not template.is_strong_beat(1)
    assert template.is_strong_beat(2)


def test_avartana_boundaries() -> None:
    template = TalaTemplate("Adi", aksharas=8, kala=2)
    assert template.is_avartana_start(0)
    assert template.is_avartana_start(16)
    assert not template.is_avartana_start(8)


def test_free_alapana_has_no_beats() -> None:
    """Anibaddha material carries no tala, so nothing is a strong beat."""
    template = TalaTemplate("Free (Alapana)", aksharas=0, kala=1, metered=False)
    assert not template.is_strong_beat(0)
    assert not template.is_avartana_start(0)
