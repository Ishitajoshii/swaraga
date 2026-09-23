"""B0 - raga-grammar random walk.

Scores every candidate equally and lets the decoder's mask do all the work.
It is the floor of the roadmap: whatever it scores is what the *constraint
alone* achieves, with no musical knowledge whatsoever.

Its purpose is to make the constraint ablation honest. B0 will post a perfect
raga-conformance score, which is precisely why conformance is a contract check
rather than a result (PRD section 9.1).
"""

from __future__ import annotations

from typing import Dict, Sequence


class GrammarRandomWalk:
    """Uniform over whatever the grammar permits."""

    name = "B0"
    description = "raga-grammar random walk"

    def fit(self, windows) -> "GrammarRandomWalk":  # noqa: ANN001 - uniform API
        """No parameters to learn; accepted so every model trains alike."""
        return self

    def next_scores(self, context: Sequence[int]) -> Dict[int, float]:
        # Empty scores make the decoder fall back to a uniform draw over the
        # legal set, which is exactly this model's definition.
        return {}
