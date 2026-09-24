"""Degree and conditioning vocabularies.

A model trained with one index assignment is meaningless if decoded with
another, so the mapping's stability is the thing worth pinning here.
"""

from __future__ import annotations

import pytest

from swaraga.vocab import (
    DEFAULT_DEGREE_RANGE,
    PAD_INDEX,
    ConditionVocab,
    DegreeVocab,
)
from swaraga.windows import FOREIGN_DEGREE, REST_DEGREE, Window


@pytest.fixture(scope="module")
def vocab() -> DegreeVocab:
    return DegreeVocab()


def window(raga="Mohanam", tala="Adi", composer="Tyagaraja") -> Window:
    return Window(record_id="x", raga=raga, tala=tala, composer=composer,
                  composer_group="Trinity", mela=28, start=0,
                  context=[], target=[], context_degrees=[], target_degrees=[])


# --- degrees ----------------------------------------------------------------

def test_padding_is_index_zero(vocab) -> None:
    assert PAD_INDEX == 0
    assert vocab.decode(PAD_INDEX) is None


def test_round_trip_over_the_whole_range(vocab) -> None:
    for degree in range(DEFAULT_DEGREE_RANGE[0], DEFAULT_DEGREE_RANGE[1] + 1):
        assert vocab.decode(vocab.encode(degree)) == degree


def test_markers_round_trip(vocab) -> None:
    for marker in (REST_DEGREE, FOREIGN_DEGREE):
        assert vocab.decode(vocab.encode(marker)) == marker


def test_rest_and_foreign_stay_distinct(vocab) -> None:
    """Conflating them would turn a data error into silence."""
    assert vocab.encode(REST_DEGREE) != vocab.encode(FOREIGN_DEGREE)


def test_no_real_degree_collides_with_padding(vocab) -> None:
    degrees = list(range(DEFAULT_DEGREE_RANGE[0], DEFAULT_DEGREE_RANGE[1] + 1))
    for degree in degrees + [REST_DEGREE, FOREIGN_DEGREE]:
        assert vocab.encode(degree) != PAD_INDEX


def test_out_of_range_degrees_fold_onto_foreign(vocab) -> None:
    """A wild degree must not silently alias onto a real note."""
    assert vocab.encode(9999) == vocab.encode(FOREIGN_DEGREE)


def test_indices_are_contiguous_from_zero(vocab) -> None:
    """Embedding layers need a dense range."""
    indices = {vocab.encode(d) for d in vocab.degrees}
    assert indices == set(range(1, vocab.size))


def test_mapping_is_stable_across_instances() -> None:
    """A checkpoint must stay readable; the assignment cannot drift."""
    a, b = DegreeVocab(), DegreeVocab()
    for degree in (0, 5, 13, REST_DEGREE, FOREIGN_DEGREE):
        assert a.encode(degree) == b.encode(degree)


def test_sequence_helpers(vocab) -> None:
    sequence = [0, 3, REST_DEGREE, 7, FOREIGN_DEGREE]
    assert vocab.decode_sequence(vocab.encode_sequence(sequence)) == sequence


def test_is_musical(vocab) -> None:
    assert vocab.is_musical(vocab.encode(4))
    assert not vocab.is_musical(vocab.encode(REST_DEGREE))
    assert not vocab.is_musical(vocab.encode(FOREIGN_DEGREE))
    assert not vocab.is_musical(PAD_INDEX)


def test_size_covers_everything(vocab) -> None:
    span = DEFAULT_DEGREE_RANGE[1] - DEFAULT_DEGREE_RANGE[0] + 1
    assert vocab.size == span + 2 + 1      # degrees + 2 markers + padding


# --- conditioning -----------------------------------------------------------

def test_condition_vocab_from_windows() -> None:
    vocab = ConditionVocab.from_windows([
        window(raga="Mohanam"), window(raga="Hindolam"), window(raga="Mohanam"),
    ])
    assert vocab.n_ragas == 3                       # 2 seen + unknown
    assert vocab.raga("Mohanam") != vocab.raga("Hindolam")


def test_unseen_values_degrade_to_unknown() -> None:
    """An unknown raga at inference must not crash the model."""
    vocab = ConditionVocab.from_windows([window(raga="Mohanam")])
    assert vocab.raga("Kalyani") == ConditionVocab.UNKNOWN
    assert vocab.tala("Jhampa") == ConditionVocab.UNKNOWN
    assert vocab.composer("Nobody") == ConditionVocab.UNKNOWN


def test_index_zero_is_reserved_for_unknown() -> None:
    vocab = ConditionVocab.from_windows([window(raga="Mohanam")])
    assert vocab.raga("Mohanam") != ConditionVocab.UNKNOWN


def test_condition_indexing_is_order_independent() -> None:
    """Sorted assignment, so window order cannot change the mapping."""
    a = ConditionVocab.from_windows([window(raga="Mohanam"), window(raga="Abhogi")])
    b = ConditionVocab.from_windows([window(raga="Abhogi"), window(raga="Mohanam")])
    assert a.ragas == b.ragas


def test_empty_condition_vocab_is_safe() -> None:
    vocab = ConditionVocab.from_windows([])
    assert vocab.n_ragas == 1
    assert vocab.raga("anything") == ConditionVocab.UNKNOWN
