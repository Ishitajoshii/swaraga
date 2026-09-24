"""Vocabularies mapping musical values onto contiguous model indices.

Scale degrees are sparse and signed - real notes run 0..13 across the register,
while rests and foreign swaras sit at -1000 and -1001 so they cannot collide
with a real degree (see :mod:`swaraga.windows`). Embedding layers need dense
indices from 0, so this module owns that translation and nothing else does.

Keeping it separate matters because the mapping has to be *stable*: a model
trained with one index assignment is meaningless if decoded with another.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from .windows import FOREIGN_DEGREE, REST_DEGREE, Window

#: Index reserved for padding shorter sequences. Never a real musical value.
PAD_INDEX = 0

#: The register a model may work in, as scale degrees. Wider than the corpus
#: uses (0..13) so a model is not structurally unable to emit a note the
#: constrained decoder would allow.
DEFAULT_DEGREE_RANGE = (-7, 21)


@dataclass(frozen=True)
class DegreeVocab:
    """Bidirectional map between scale degrees and model indices.

    Index 0 is padding; then the special markers; then the degree range in
    ascending order. The ordering is deterministic so that a checkpoint stays
    readable across runs.
    """

    low: int = DEFAULT_DEGREE_RANGE[0]
    high: int = DEFAULT_DEGREE_RANGE[1]

    @property
    def degrees(self) -> List[int]:
        """Every degree this vocabulary can represent, in index order."""
        return [REST_DEGREE, FOREIGN_DEGREE] + list(range(self.low, self.high + 1))

    @property
    def size(self) -> int:
        return len(self.degrees) + 1        # +1 for PAD

    def _index_of(self) -> Dict[int, int]:
        return {degree: i + 1 for i, degree in enumerate(self.degrees)}

    def encode(self, degree: int) -> int:
        """Degree -> model index. Out-of-range degrees fold onto FOREIGN."""
        table = self._index_of()
        return table.get(degree, table[FOREIGN_DEGREE])

    def decode(self, index: int) -> Optional[int]:
        """Model index -> degree. ``None`` for padding."""
        if index == PAD_INDEX:
            return None
        degrees = self.degrees
        position = index - 1
        if 0 <= position < len(degrees):
            return degrees[position]
        return FOREIGN_DEGREE

    def encode_sequence(self, sequence: Sequence[int]) -> List[int]:
        table = self._index_of()
        foreign = table[FOREIGN_DEGREE]
        return [table.get(degree, foreign) for degree in sequence]

    def decode_sequence(self, indices: Sequence[int]) -> List[int]:
        return [d for d in (self.decode(i) for i in indices) if d is not None]

    def is_musical(self, index: int) -> bool:
        """Is this index a note, rather than padding, a rest or a data error?"""
        degree = self.decode(index)
        return degree is not None and degree not in (REST_DEGREE, FOREIGN_DEGREE)


@dataclass(frozen=True)
class ConditionVocab:
    """Indices for the categorical conditioning fields (raga, tala, composer).

    Built from the training data, with index 0 reserved for values never seen
    during training - so an unknown raga at inference degrades to a generic
    embedding instead of crashing.
    """

    ragas: Dict[str, int]
    talas: Dict[str, int]
    composers: Dict[str, int]

    UNKNOWN = 0

    @classmethod
    def from_windows(cls, windows: Iterable[Window]) -> "ConditionVocab":
        ragas, talas, composers = set(), set(), set()
        for window in windows:
            ragas.add(window.raga)
            talas.add(window.tala)
            composers.add(window.composer)
        return cls(
            ragas=_index_map(ragas),
            talas=_index_map(talas),
            composers=_index_map(composers),
        )

    def raga(self, name: str) -> int:
        return self.ragas.get(name, self.UNKNOWN)

    def tala(self, name: str) -> int:
        return self.talas.get(name, self.UNKNOWN)

    def composer(self, name: str) -> int:
        return self.composers.get(name, self.UNKNOWN)

    @property
    def n_ragas(self) -> int:
        return len(self.ragas) + 1

    @property
    def n_talas(self) -> int:
        return len(self.talas) + 1

    @property
    def n_composers(self) -> int:
        return len(self.composers) + 1


def _index_map(values: Iterable[str]) -> Dict[str, int]:
    """Sorted, 1-based index map; 0 stays reserved for unknown."""
    return {value: i + 1 for i, value in enumerate(sorted(values))}
