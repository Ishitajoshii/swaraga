"""Windowing and scale-degree encoding for the task ladder (PRD sections 3, 4).

A *window* is one training example: some context notes plus the continuation
the model must predict.  Windows are cut at stride 1 and never cross a
composition boundary, so no example mixes two pieces.

Two encodings are produced for every window:

absolute
    the raga's own swaras (``G3``, ``M1``, ``S'``) - what the model must emit
degree
    each swara's index within its raga's scale - what the model reasons over,
    so that all ragas pool into one training set (PRD section 4)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd

from . import config
from .grammar import RagaGrammar, RagaGrammarLibrary, TalaTemplate

#: Markers in degree space. They sit far outside any reachable scale index:
#: degrees run from ``-n`` to ``2n`` across the allowed register, so a small
#: sentinel like -1 would collide with the note one degree below Sa.
REST_DEGREE = -1000

#: A swara that is not in its own raga's scale - i.e. a data error. Kept
#: distinct from a rest so that a corrupt note is never silently read as
#: silence. ``hindolam_keerthanam_001`` contains one (a rishabha in a raga that
#: has none), and it must stay visible rather than vanishing into a rest.
FOREIGN_DEGREE = -1001

#: Degrees that are not playable notes.
NON_NOTE_DEGREES = frozenset({REST_DEGREE, FOREIGN_DEGREE})


def is_note(degree: int) -> bool:
    """Is this degree an actual swara, rather than a rest or a data error?"""
    return degree not in NON_NOTE_DEGREES

#: The task ladder from PRD section 3: (context, horizon) in notated positions.
#: T3 is expressed in positions too, resolved per composition from its tala.
RUNGS: Dict[str, Dict[str, object]] = {
    "T1": {"context": 12, "horizon": 4, "unit": "notes",
           "label": "12 notes -> next 4"},
    "T2": {"context": 16, "horizon": 8, "unit": "notes",
           "label": "16 notes -> next 8 (half avartana)"},
    "T3": {"context": 4, "horizon": 2, "unit": "avartanas",
           "label": "4 avartanas -> next 2"},
}

DEFAULT_RUNG = "T2"


@dataclass
class Window:
    """One training example."""

    record_id: str
    raga: str
    tala: str
    composer: str
    composer_group: str
    mela: int
    start: int                              # position in the source sequence

    context: List[str]                      # absolute swaras
    target: List[str]                       # absolute swaras
    context_degrees: List[int]              # scale degrees (REST_DEGREE for rests)
    target_degrees: List[int]

    rung: str = DEFAULT_RUNG

    @property
    def horizon(self) -> int:
        return len(self.target)

    def as_record(self) -> Dict[str, object]:
        """Flat dict for serialisation or a DataFrame."""
        return {
            "record_id": self.record_id,
            "raga": self.raga,
            "tala": self.tala,
            "composer": self.composer,
            "composer_group": self.composer_group,
            "mela": self.mela,
            "rung": self.rung,
            "start": self.start,
            "context": self.context,
            "target": self.target,
            "context_degrees": self.context_degrees,
            "target_degrees": self.target_degrees,
        }


def to_degrees(sequence: Sequence[str], grammar: RagaGrammar) -> List[int]:
    """Map absolute swaras onto scale degrees, carrying octave into the index.

    A swara one octave up becomes ``degree + len(scale)``, so ``S`` and ``S'``
    stay distinguishable and contour across the octave break is preserved.
    Rests become :data:`REST_DEGREE`; swaras foreign to the raga become
    :data:`FOREIGN_DEGREE` rather than being folded into rests.
    """
    degrees: List[int] = []
    n = grammar.n_degrees
    for token in sequence:
        if token == config.REST:
            degrees.append(REST_DEGREE)
            continue
        base = token.rstrip("'.")
        octave = token.count("'") - token.count(".")
        degree = grammar.to_degree(base)
        degrees.append(FOREIGN_DEGREE if degree is None else degree + octave * n)
    return degrees


def from_degrees(degrees: Sequence[int], grammar: RagaGrammar) -> List[str]:
    """Inverse of :func:`to_degrees` - re-instantiate degrees as swaras.

    This is what lets a pooled degree model emit into a specific raga
    (PRD section 4).
    """
    n = grammar.n_degrees
    out: List[str] = []
    for degree in degrees:
        if degree in NON_NOTE_DEGREES:
            # A foreign swara cannot be recovered - the original token is gone
            # by this point - so it surfaces as a rest. Detection belongs
            # upstream, where `to_degrees` still has the token.
            out.append(config.REST)
            continue
        swara = grammar.from_degree(degree)
        octave = degree // n
        if octave > 0:
            swara += "'" * octave
        elif octave < 0:
            swara += "." * (-octave)
        out.append(swara)
    return out


def _horizon_and_context(rung: str, row) -> Tuple[int, int]:
    """Resolve a rung to (context, horizon) in notated positions."""
    spec = RUNGS[rung]
    if spec["unit"] == "notes":
        return int(spec["context"]), int(spec["horizon"])

    template = TalaTemplate.from_row(row)
    if not template.metered:
        # Free / anibaddha material has no avartana, so an avartana-based rung
        # cannot apply to it.
        return 0, 0
    per = template.positions_per_avartana
    return int(spec["context"]) * per, int(spec["horizon"]) * per


def windows_for_row(row, grammar: RagaGrammar, rung: str = DEFAULT_RUNG,
                    stride: int = 1) -> List[Window]:
    """Every window one composition yields at ``rung``."""
    context_len, horizon = _horizon_and_context(rung, row)
    if context_len <= 0 or horizon <= 0:
        return []

    sequence = list(row["swara_sequence"])
    span = context_len + horizon
    degrees = to_degrees(sequence, grammar)

    windows: List[Window] = []
    for start in range(0, len(sequence) - span + 1, stride):
        split = start + context_len
        end = start + span
        windows.append(
            Window(
                record_id=row["id"],
                raga=row["raga"],
                tala=row["tala"],
                composer=row["composer"],
                composer_group=row["composer_group"],
                mela=int(row["mela"]),
                start=start,
                context=sequence[start:split],
                target=sequence[split:end],
                context_degrees=degrees[start:split],
                target_degrees=degrees[split:end],
                rung=rung,
            )
        )
    return windows


def build_windows(frame: pd.DataFrame, rung: str = DEFAULT_RUNG,
                  stride: int = 1,
                  library: Optional[RagaGrammarLibrary] = None) -> List[Window]:
    """Every window the dataset yields at ``rung``."""
    if rung not in RUNGS:
        raise ValueError(f"unknown rung {rung!r}; expected one of {sorted(RUNGS)}")

    library = library or RagaGrammarLibrary()
    windows: List[Window] = []
    for _, row in frame.iterrows():
        grammar = library.for_row(row)
        windows.extend(windows_for_row(row, grammar, rung=rung, stride=stride))
    return windows


def windows_to_frame(windows: Iterable[Window]) -> pd.DataFrame:
    """Windows as a DataFrame, for inspection and for the model layers."""
    return pd.DataFrame.from_records([w.as_record() for w in windows])


def split_windows(windows: Sequence[Window],
                  splits: Dict[str, Sequence[str]]) -> Dict[str, List[Window]]:
    """Partition windows by which split their *composition* belongs to.

    Assigning by composition, not by window, is what keeps the leakage
    guarantee from PRD section 7 of the preprocessing spec: two windows that
    overlap in the source cannot land on opposite sides of the split.
    """
    owner: Dict[str, str] = {}
    for name, record_ids in splits.items():
        for record_id in record_ids:
            owner[record_id] = name

    out: Dict[str, List[Window]] = {name: [] for name in splits}
    for window in windows:
        name = owner.get(window.record_id)
        if name is not None:
            out[name].append(window)
    return out


def window_counts(frame: pd.DataFrame,
                  library: Optional[RagaGrammarLibrary] = None
                  ) -> Dict[str, Dict[str, int]]:
    """Windows available per rung - the table in PRD section 3."""
    library = library or RagaGrammarLibrary()
    counts: Dict[str, Dict[str, int]] = {}
    for rung in RUNGS:
        windows = build_windows(frame, rung=rung, library=library)
        by_raga: Dict[str, int] = {}
        for window in windows:
            by_raga[window.raga] = by_raga.get(window.raga, 0) + 1
        counts[rung] = {
            "total": len(windows),
            "compositions_contributing": len({w.record_id for w in windows}),
            "ragas_covered": len(by_raga),
            "min_per_raga": min(by_raga.values()) if by_raga else 0,
            "max_per_raga": max(by_raga.values()) if by_raga else 0,
        }
    return counts
