"""B1 - variable-order Markov model over scale degrees, with backoff.

The honest baseline at this data scale. With ~558 windows a neural model has
nothing to hold on to, but n-gram counts over *scale degrees* pool every raga
into one training set (PRD section 4) and so actually have evidence behind
them: 143 degree 4-grams recur, where per-raga absolute counts almost never do.

Backoff is stupid-backoff rather than Kneser-Ney: with counts this sparse the
smoothing method matters far less than having any backoff at all, and
stupid-backoff has no hyperparameters to tune on a validation set that is
itself only a handful of compositions.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, Sequence, Tuple

from ..windows import Window

#: Weight applied each time the model backs off one order.
BACKOFF_ALPHA = 0.4


class VariableOrderMarkov:
    """Counts degree n-grams up to ``max_order``, backing off when unseen."""

    name = "B1"
    description = "variable-order Markov over scale degrees"

    def __init__(self, max_order: int = 4, alpha: float = BACKOFF_ALPHA) -> None:
        self.max_order = max_order
        self.alpha = alpha
        # counts[order][context_tuple][next_degree] -> count
        self.counts: Dict[int, Dict[Tuple[int, ...], Dict[int, int]]] = {
            order: defaultdict(lambda: defaultdict(int))
            for order in range(max_order + 1)
        }
        self.n_observations = 0

    # -- training -----------------------------------------------------------

    def fit(self, windows: Iterable[Window]) -> "VariableOrderMarkov":
        """Count n-grams over each window's full degree sequence.

        Context and target are concatenated: within a window they are one
        continuous melody, and the split point is an artefact of the task, not
        of the music.
        """
        for window in windows:
            sequence = list(window.context_degrees) + list(window.target_degrees)
            self._count_sequence(sequence)
        return self

    def _count_sequence(self, sequence: Sequence[int]) -> None:
        for position in range(len(sequence)):
            following = sequence[position]
            for order in range(self.max_order + 1):
                if position - order < 0:
                    break
                context = tuple(sequence[position - order:position])
                self.counts[order][context][following] += 1
                self.n_observations += 1

    def fit_sequences(self, sequences: Iterable[Sequence[int]]) -> "VariableOrderMarkov":
        """Count independent source phrases once, without joining boundaries."""
        for sequence in sequences:
            self._count_sequence(sequence)
        return self

    # -- inference ----------------------------------------------------------

    def next_scores(self, context: Sequence[int]) -> Dict[int, float]:
        """Interpolate the highest-order match down to the unigram."""
        scores: Dict[int, float] = defaultdict(float)
        weight = 1.0
        found_any = False

        for order in range(min(self.max_order, len(context)), -1, -1):
            key = tuple(context[len(context) - order:]) if order else ()
            table = self.counts[order].get(key)
            if table:
                total = sum(table.values())
                for degree, count in table.items():
                    scores[degree] += weight * (count / total)
                found_any = True
            weight *= self.alpha

        if not found_any:
            return {}
        return dict(scores)

    # -- evaluation support -------------------------------------------------

    def probability(self, context: Sequence[int], following: int) -> float:
        """Normalised P(following | context), for perplexity."""
        scores = self.next_scores(context)
        total = sum(scores.values())
        if total <= 0:
            return 0.0
        return scores.get(following, 0.0) / total

    @property
    def n_distinct_ngrams(self) -> int:
        return sum(len(table) for table in self.counts[self.max_order].values())
