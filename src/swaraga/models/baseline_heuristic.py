"""B0.5 - the "continue the current direction" heuristic.

This is the bar every learned model must clear (PRD section 8.1).

It is a strong baseline on this corpus by construction: 16% of all 4-grams are
pure scalar runs, because the repertoire is heavy on geetams and varisais. A
model that simply keeps walking the scale in the direction it was already going
will therefore look good on exactly the material that dominates the data.

Reporting a learned model that cannot beat this is a legitimate result, and it
is the evidence the data-scaling argument rests on.
"""

from __future__ import annotations

from typing import Dict, Sequence

from ..decode import infer_direction
from ..grammar import ASCENDING, DESCENDING
from ..windows import REST_DEGREE, is_note


class DirectionHeuristic:
    """Keep moving by one scale degree in the direction of travel."""

    name = "B0.5"
    description = "continue the current direction"

    def __init__(self, step_decay: float = 0.35, turn_weight: float = 0.15,
                 rest_weight: float = 0.05) -> None:
        #: How fast preference falls off for steps larger than one degree.
        self.step_decay = step_decay
        #: Weight given to reversing direction, so the walk is not rigid.
        self.turn_weight = turn_weight
        self.rest_weight = rest_weight

    def fit(self, windows) -> "DirectionHeuristic":  # noqa: ANN001 - uniform API
        """No parameters to learn from data; the prior is the whole model."""
        return self

    def next_scores(self, context: Sequence[int]) -> Dict[int, float]:
        real = [d for d in context if is_note(d)]
        if not real:
            return {}

        current = real[-1]
        direction = infer_direction(context)
        forward = 1 if direction == ASCENDING else -1 if direction == DESCENDING else 0

        scores: Dict[int, float] = {REST_DEGREE: self.rest_weight}

        # Prefer small steps, strongly preferring one degree of travel.
        for step in range(1, 5):
            weight = self.step_decay ** (step - 1)
            if forward == 0:
                # No established direction: both ways equally.
                scores[current + step] = weight
                scores[current - step] = weight
            else:
                scores[current + forward * step] = weight
                scores[current - forward * step] = weight * self.turn_weight

        # Repeating a note is always available, but never the default.
        scores[current] = self.turn_weight

        return {degree: weight for degree, weight in scores.items() if weight > 0}
