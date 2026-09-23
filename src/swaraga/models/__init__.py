"""Models for melodic continuation (PRD section 8).

All v1 models are pure Python / numpy and share one interface:
``next_scores(context) -> {degree: score}``, consumed by
:class:`swaraga.decode.ConstrainedDecoder`.  Keeping the baselines
framework-free keeps them auditable, which matters when they are the bar a
neural model has to clear.

``neural.py`` (PyTorch) arrives at the M1 milestone.
"""

from .baseline_grammar import GrammarRandomWalk
from .baseline_heuristic import DirectionHeuristic
from .baseline_ngram import VariableOrderMarkov
from .retrieval import RetrievalModel

#: Every baseline, in roadmap order (PRD section 8).
BASELINES = {
    "B0": GrammarRandomWalk,
    "B0.5": DirectionHeuristic,
    "B1": VariableOrderMarkov,
    "B2": RetrievalModel,
}

__all__ = [
    "GrammarRandomWalk",
    "DirectionHeuristic",
    "VariableOrderMarkov",
    "RetrievalModel",
    "BASELINES",
]
