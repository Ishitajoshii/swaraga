"""B2 - retrieval and adaptation.

Finds the training context whose *contour* most resembles the query, then
proposes that neighbour's continuation.  Because everything is in scale-degree
space, a phrase learned in Mohanam can be transplanted into Hindolam and still
come out in-raga once the decoder re-instantiates the degrees.

This is the baseline that tends to work best when data is this scarce: with
~558 windows there is more signal in "something very like this happened before"
than in any distribution estimated from the same counts.

Its weakness is the flip side and must be watched: retrieval can copy. The
novelty metric in :mod:`swaraga.evaluate` exists largely to catch it.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ..windows import REST_DEGREE, Window, is_note


class RetrievalModel:
    """k-nearest-neighbour over degree contours."""

    name = "B2"
    description = "retrieval + adaptation"

    def __init__(self, k: int = 5, contour_length: int = 6,
                 same_raga_bonus: float = 0.25) -> None:
        self.k = k
        #: How many trailing context notes define the contour used for matching.
        self.contour_length = contour_length
        #: Extra similarity credit when the neighbour is from the same raga.
        self.same_raga_bonus = same_raga_bonus
        # (contour, last context degree, continuation, raga)
        self.entries: List[Tuple[Tuple[int, ...], int, List[int], str]] = []

    # -- training -----------------------------------------------------------

    def fit(self, windows: Iterable[Window]) -> "RetrievalModel":
        """Index every window as (contour, anchor, continuation, raga).

        The anchor is the neighbour's last context degree.  It is what makes
        adaptation possible: the continuation is stored as a *step away from
        the anchor*, so it can be re-hung at whatever register the query ends
        on instead of being pasted in at its original pitch.
        """
        self.entries = []
        for window in windows:
            contour = self._contour(window.context_degrees)
            real = [d for d in window.context_degrees if is_note(d)]
            if contour and real and window.target_degrees:
                self.entries.append(
                    (contour, real[-1], list(window.target_degrees), window.raga)
                )
        return self

    def _contour(self, degrees: Sequence[int]) -> Tuple[int, ...]:
        """Trailing context as *intervals*, which is what transfers across ragas.

        Absolute degrees anchor a phrase to a register; the intervals between
        them are the shape, and the shape is what a different raga can reuse.
        """
        real = [d for d in degrees if is_note(d)]
        tail = real[-self.contour_length:]
        if len(tail) < 2:
            return ()
        return tuple(b - a for a, b in zip(tail, tail[1:]))

    # -- inference ----------------------------------------------------------

    def _similarity(self, query: Tuple[int, ...],
                    candidate: Tuple[int, ...]) -> float:
        """Inverse mean absolute interval difference over the shared suffix."""
        span = min(len(query), len(candidate))
        if span == 0:
            return 0.0
        distance = sum(
            abs(a - b) for a, b in zip(query[-span:], candidate[-span:])
        ) / span
        # Longer agreement is stronger evidence than a short accidental match.
        coverage = span / max(len(query), 1)
        return coverage / (1.0 + distance)

    def next_scores(self, context: Sequence[int],
                    raga: Optional[str] = None) -> Dict[int, float]:
        """Score the first step of each neighbour's continuation."""
        query = self._contour(context)
        if not query or not self.entries:
            return {}

        scored: List[Tuple[float, int, List[int]]] = []
        for contour, entry_anchor, continuation, entry_raga in self.entries:
            similarity = self._similarity(query, contour)
            if raga is not None and entry_raga == raga:
                similarity *= (1.0 + self.same_raga_bonus)
            if similarity > 0:
                scored.append((similarity, entry_anchor, continuation))

        if not scored:
            return {}

        scored.sort(key=lambda item: item[0], reverse=True)
        real = [d for d in context if is_note(d)]
        anchor = real[-1] if real else 0

        scores: Dict[int, float] = defaultdict(float)
        for similarity, entry_anchor, continuation in scored[:self.k]:
            first = continuation[0]
            if first == REST_DEGREE:
                scores[REST_DEGREE] += similarity
                continue
            # Transplant the neighbour's *step*, not its absolute pitch, so the
            # phrase lands in the query's register.
            scores[anchor + (first - entry_anchor)] += similarity

        return dict(scores)
