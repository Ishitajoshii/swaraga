"""Composer normalisation and Trinity grouping (PRD sections 2 and 4).

Trinity membership is read from the controlled dictionary, never inferred from
spelling similarity.  A name that is not in the dictionary is kept verbatim and
grouped as ``Unknown / Unclassified`` so nothing is silently discarded.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .. import config
from ..text_norm import clean_text, normalise_key


@dataclass
class ComposerResult:
    """Outcome of normalising one composer string."""

    composer: str                       # canonical name
    composer_raw: str                   # original value, cleaned of mojibake only
    composer_group: str                 # Trinity / Other Known / Unknown
    certainty: str                      # attested / attributed / traditional / unknown
    attribution_note: Optional[str] = None
    matched: bool = True                # False when the name was not in the dictionary
    issues: List[str] = field(default_factory=list)

    @property
    def is_trinity(self) -> bool:
        return self.composer_group == config.GROUP_TRINITY


class ComposerNormalizer:
    """Maps free-text composer strings onto the controlled vocabulary."""

    def __init__(self, dictionary_path: Path = config.COMPOSER_DICT) -> None:
        self.dictionary_path = Path(dictionary_path)
        with self.dictionary_path.open(encoding="utf-8") as handle:
            self._raw = json.load(handle)

        self.composers: Dict[str, dict] = self._raw["composers"]
        self.attributed_forms: Dict[str, dict] = {
            key: value
            for key, value in self._raw.get("attributed_forms", {}).items()
            if not key.startswith("_")
        }

        # alias key -> canonical name
        self._alias_index: Dict[str, str] = {}
        for canonical, entry in self.composers.items():
            for alias in entry.get("aliases", [canonical]):
                self._alias_index[normalise_key(alias)] = canonical
            self._alias_index[normalise_key(canonical)] = canonical

        # hedged attribution key -> (canonical, certainty, note)
        self._attributed_index: Dict[str, tuple] = {}
        for source_name, entry in self.attributed_forms.items():
            self._attributed_index[normalise_key(source_name)] = (
                entry["canonical"],
                entry.get("certainty", "attributed"),
                entry.get("attribution_note"),
            )

    # -- lookups ------------------------------------------------------------

    def group_of(self, canonical: str) -> str:
        """Composer group for an already-canonical name."""
        entry = self.composers.get(canonical)
        return entry["group"] if entry else config.GROUP_UNKNOWN

    @property
    def trinity_members(self) -> List[str]:
        return [
            name
            for name, entry in self.composers.items()
            if entry["group"] == config.GROUP_TRINITY
        ]

    # -- main entry point ---------------------------------------------------

    def normalize(self, value: str) -> ComposerResult:
        """Normalise one composer string."""
        cleaned, issues = clean_text(value or "")
        key = normalise_key(cleaned)

        if not key:
            return ComposerResult(
                composer="Unknown",
                composer_raw=cleaned,
                composer_group=config.GROUP_UNKNOWN,
                certainty="unknown",
                matched=False,
                issues=issues + ["composer_missing"],
            )

        # Hedged attributions are checked first; they are more specific than
        # the plain alias index and must not be flattened into it.
        if key in self._attributed_index:
            canonical, certainty, note = self._attributed_index[key]
            return ComposerResult(
                composer=canonical,
                composer_raw=cleaned,
                composer_group=self.group_of(canonical),
                certainty=certainty,
                attribution_note=note,
                matched=True,
                issues=issues + ["composer_attribution_hedged"],
            )

        if key in self._alias_index:
            canonical = self._alias_index[key]
            entry = self.composers[canonical]
            result_issues = list(issues)
            if cleaned != canonical:
                result_issues.append(f"composer_alias_mapped:{cleaned}->{canonical}")
            return ComposerResult(
                composer=canonical,
                composer_raw=cleaned,
                composer_group=entry["group"],
                certainty=entry.get("certainty", "attested"),
                matched=True,
                issues=result_issues,
            )

        # Unknown composer: preserved, never dropped, never guessed into Trinity.
        return ComposerResult(
            composer=cleaned,
            composer_raw=cleaned,
            composer_group=config.GROUP_UNKNOWN,
            certainty="unknown",
            matched=False,
            issues=issues + ["composer_not_in_dictionary"],
        )
