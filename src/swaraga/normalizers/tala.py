"""Tala name normalisation (PRD section 3).

Besides the canonical name the dictionary supplies the authoritative akshara
count and a ``metered`` flag, which lets the pipeline validate the source
``tala_aksharas`` column and mark free / anibaddha material such as alapana.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .. import config
from ..text_norm import clean_text, normalise_key


@dataclass
class TalaResult:
    """Outcome of normalising one tala string."""

    tala: str                           # canonical name
    tala_raw: str                       # original value
    aksharas: Optional[int] = None      # authoritative count from the dictionary
    metered: bool = True
    structure: Optional[str] = None
    matched: bool = True
    issues: List[str] = field(default_factory=list)


class TalaNormalizer:
    """Maps free-text tala strings onto the controlled vocabulary."""

    def __init__(self, dictionary_path: Path = config.TALA_DICT) -> None:
        self.dictionary_path = Path(dictionary_path)
        with self.dictionary_path.open(encoding="utf-8") as handle:
            self._raw = json.load(handle)

        self.talas: Dict[str, dict] = self._raw["talas"]

        self._alias_index: Dict[str, str] = {}
        for canonical, entry in self.talas.items():
            self._alias_index[normalise_key(canonical)] = canonical
            for alias in entry.get("aliases", []):
                self._alias_index[normalise_key(alias)] = canonical

    def normalize(self, value: str, source_aksharas: Optional[int] = None) -> TalaResult:
        """Normalise one tala string and validate its akshara count.

        ``source_aksharas`` is the value from the dataset; a disagreement with
        the dictionary is recorded as an issue and the dictionary wins.
        """
        cleaned, issues = clean_text(value or "")
        key = normalise_key(cleaned)

        if not key:
            return TalaResult(
                tala="Unknown",
                tala_raw=cleaned,
                matched=False,
                issues=issues + ["tala_missing"],
            )

        if key in self._alias_index:
            canonical = self._alias_index[key]
            entry = self.talas[canonical]
            result_issues = list(issues)
            if cleaned != canonical:
                result_issues.append(f"tala_alias_mapped:{cleaned}->{canonical}")

            aksharas = entry.get("aksharas")
            if (
                source_aksharas is not None
                and aksharas is not None
                and int(source_aksharas) != int(aksharas)
            ):
                result_issues.append(
                    f"tala_aksharas_mismatch:{canonical}:"
                    f"source={int(source_aksharas)},expected={int(aksharas)}"
                )

            return TalaResult(
                tala=canonical,
                tala_raw=cleaned,
                aksharas=aksharas,
                metered=bool(entry.get("metered", True)),
                structure=entry.get("structure"),
                matched=True,
                issues=result_issues,
            )

        return TalaResult(
            tala=cleaned,
            tala_raw=cleaned,
            aksharas=int(source_aksharas) if source_aksharas is not None else None,
            matched=False,
            issues=issues + ["tala_not_in_dictionary"],
        )
