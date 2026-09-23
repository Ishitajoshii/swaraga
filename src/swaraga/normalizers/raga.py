"""Raga name normalisation (PRD section 3).

The dictionary also carries each raga's parent melakarta, which lets the
pipeline cross-check the ``mela`` column in the source data and fall back to
the dictionary when the column disagrees.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .. import config
from ..text_norm import clean_text, normalise_key


@dataclass
class RagaResult:
    """Outcome of normalising one raga string."""

    raga: str                       # canonical name
    raga_raw: str                   # original value
    mela: Optional[int] = None      # parent melakarta from the dictionary
    notes: Optional[str] = None     # musicological caveat, if the dictionary has one
    matched: bool = True
    issues: List[str] = field(default_factory=list)


class RagaNormalizer:
    """Maps free-text raga strings onto the controlled vocabulary."""

    def __init__(self, dictionary_path: Path = config.RAGA_DICT) -> None:
        self.dictionary_path = Path(dictionary_path)
        with self.dictionary_path.open(encoding="utf-8") as handle:
            self._raw = json.load(handle)

        self.ragas: Dict[str, dict] = self._raw["ragas"]

        self._alias_index: Dict[str, str] = {}
        for canonical, entry in self.ragas.items():
            self._alias_index[normalise_key(canonical)] = canonical
            for alias in entry.get("aliases", []):
                self._alias_index[normalise_key(alias)] = canonical

    def mela_of(self, canonical: str) -> Optional[int]:
        entry = self.ragas.get(canonical)
        return entry.get("mela") if entry else None

    def normalize(self, value: str) -> RagaResult:
        """Normalise one raga string."""
        cleaned, issues = clean_text(value or "")
        key = normalise_key(cleaned)

        if not key:
            return RagaResult(
                raga="Unknown",
                raga_raw=cleaned,
                matched=False,
                issues=issues + ["raga_missing"],
            )

        if key in self._alias_index:
            canonical = self._alias_index[key]
            entry = self.ragas[canonical]
            result_issues = list(issues)
            if cleaned != canonical:
                result_issues.append(f"raga_alias_mapped:{cleaned}->{canonical}")
            return RagaResult(
                raga=canonical,
                raga_raw=cleaned,
                mela=entry.get("mela"),
                notes=entry.get("notes"),
                matched=True,
                issues=result_issues,
            )

        return RagaResult(
            raga=cleaned,
            raga_raw=cleaned,
            matched=False,
            issues=issues + ["raga_not_in_dictionary"],
        )
