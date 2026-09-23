"""Controlled-vocabulary normalisers for composer, raga and tala.

Each normaliser is backed by a JSON dictionary under ``config/`` and returns a
result object that keeps the original value for traceability (PRD section 4).
"""

from .composer import ComposerNormalizer, ComposerResult
from .raga import RagaNormalizer, RagaResult
from .tala import TalaNormalizer, TalaResult

__all__ = [
    "ComposerNormalizer",
    "ComposerResult",
    "RagaNormalizer",
    "RagaResult",
    "TalaNormalizer",
    "TalaResult",
]
