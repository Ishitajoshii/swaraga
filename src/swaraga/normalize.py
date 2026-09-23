"""Stage 2: cleaned_dataset.parquet -> normalized_dataset.parquet.

Applies the controlled vocabularies (PRD sections 2 and 4), rebuilds the
musical representation from the authoritative notation (PRD section 5) and
preserves lyrics and metadata rather than dropping them (PRD section 3).

Why the notation is re-tokenised rather than reused
---------------------------------------------------
The source ``tokens`` column is not usable as a training target:

- every note carries the same ``GMK_AHAT`` gamaka tag, so the tag is noise;
  the real ornamentation lives in ``gamaka_annotations_json``
- swara variants are almost all written ``_2`` regardless of the raga, so the
  column contradicts the raga's own scale
- rests are dropped entirely, losing every karvai in the dataset

``sections_json`` holds the human notation those tokens were derived from, so
the pipeline re-derives the sequence from it.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pandas as pd

from . import config
from .melakarta import MELAKARTA_NAMES, full_scale_for_mela
from .notation import parse_scale_string, parse_sections, to_swara_sequence, to_token_sequence
from .normalizers import ComposerNormalizer, RagaNormalizer, TalaNormalizer
from .quality_log import QualityLog
from .period import parse_period

STAGE = "normalize"


def _as_list(value: Any) -> List[Any]:
    """Coerce a cell that may be None, a numpy array or a list into a list."""
    if value is None:
        return []
    if hasattr(value, "tolist"):
        return list(value.tolist())
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _log_issues(log: QualityLog, record_id: str, issues: List[str], field_name: str) -> None:
    for issue in issues:
        code = issue.partition(":")[0]
        severity = "warning" if code.endswith(("not_in_dictionary", "missing")) else "info"
        log.add(STAGE, code, issue, record_id=record_id,
                severity=severity, field_name=field_name)


def normalize(
    frame: pd.DataFrame,
    log: QualityLog,
    composer_normalizer: Optional[ComposerNormalizer] = None,
    raga_normalizer: Optional[RagaNormalizer] = None,
    tala_normalizer: Optional[TalaNormalizer] = None,
) -> pd.DataFrame:
    """Run the full normalisation stage."""
    composers = composer_normalizer or ComposerNormalizer()
    ragas = raga_normalizer or RagaNormalizer()
    talas = tala_normalizer or TalaNormalizer()

    records: List[Dict[str, Any]] = []

    for _, row in frame.iterrows():
        record_id = row["id"]

        # -- composer (PRD 2, 4) -------------------------------------------
        composer = composers.normalize(row["composer"])
        _log_issues(log, record_id, composer.issues, "composer")
        if not composer.matched:
            log.warning(STAGE, "composer_unmapped",
                        f"{row['composer']!r} is not in the controlled vocabulary; "
                        "grouped as Unknown / Unclassified",
                        record_id=record_id, field_name="composer")

        # -- raga -----------------------------------------------------------
        raga = ragas.normalize(row["raga"])
        _log_issues(log, record_id, raga.issues, "raga")

        mela = int(row["mela"])
        if raga.mela is not None and raga.mela != mela:
            log.warning(
                STAGE, "mela_disagrees_with_dictionary",
                f"record says mela {mela}, raga dictionary says {raga.mela} "
                f"for {raga.raga}; using the record",
                record_id=record_id, field_name="mela",
                before=mela, after=raga.mela,
            )
        if raga.notes:
            log.info(STAGE, "raga_musicological_note", raga.notes,
                     record_id=record_id, field_name="raga")

        # -- tala -----------------------------------------------------------
        tala = talas.normalize(row["tala"], row.get("tala_aksharas"))
        _log_issues(log, record_id, tala.issues, "tala")

        # -- period ---------------------------------------------------------
        period = parse_period(row.get("period", ""))
        if period.issues:
            _log_issues(log, record_id, period.issues, "period")

        # -- musical representation (PRD 5) ---------------------------------
        sections_raw = json.loads(row["sections_json"])
        parsed = parse_sections(sections_raw, mela)

        swara_sequence = to_swara_sequence(parsed)
        token_sequence = to_token_sequence(parsed, tala=tala.tala)

        sections = [
            {
                "name": section.name,
                "notation": section.raw_notation,
                "lyrics": section.lyrics,
                "swara_sequence": to_swara_sequence([section]),
                "n_swaras": len(section.notes),
                "n_rests": section.n_rests,
            }
            for section in parsed
        ]

        has_lyrics = any(section["lyrics"] for section in sections)
        if not has_lyrics:
            log.info(STAGE, "lyrics_absent",
                     "no lyrics on any section (kept as empty strings, not dropped)",
                     record_id=record_id, field_name="sections_json")

        try:
            gamakas = json.loads(row.get("gamaka_annotations_json") or "{}")
        except ValueError:
            gamakas = {}
            log.warning(STAGE, "gamaka_unparseable",
                        "gamaka_annotations_json could not be read; kept empty",
                        record_id=record_id, field_name="gamaka_annotations_json")

        records.append(
            {
                # identity
                "id": record_id,
                "title": row["title"],
                # conditioning fields (PRD 8)
                "composer": composer.composer,
                "composer_group": composer.composer_group,
                "raga": raga.raga,
                "tala": tala.tala,
                # traceability (PRD 4)
                "composer_raw": composer.composer_raw,
                "composer_certainty": composer.certainty,
                "composer_attribution_note": composer.attribution_note,
                "raga_raw": raga.raga_raw,
                "tala_raw": tala.tala_raw,
                # musical context
                "mela": mela,
                "mela_name": MELAKARTA_NAMES[mela],
                "raga_scale": full_scale_for_mela(mela),
                "arohanam": parse_scale_string(row.get("arohanam", ""), mela),
                "avarohanam": parse_scale_string(row.get("avarohanam", ""), mela),
                "arohanam_raw": row.get("arohanam", ""),
                "avarohanam_raw": row.get("avarohanam", ""),
                "tala_aksharas": tala.aksharas,
                "tala_structure": tala.structure,
                "is_metered": tala.metered,
                "speed": row.get("speed"),
                "sa_hz": float(row["sa_hz"]) if pd.notna(row.get("sa_hz")) else None,
                "period": period.text,
                "period_century": period.century,
                "composer_birth_year": period.birth_year,
                "composer_death_year": period.death_year,
                # sequences (PRD 5)
                "swara_sequence": swara_sequence,
                "token_sequence": token_sequence,
                "n_swaras": int(row["n_swaras"]),
                "n_rests": int(row["n_rests"]),
                "sequence_length": len(swara_sequence),
                "n_sections": len(sections),
                "length_flag": row["length_flag"],
                # preserved content (PRD 3)
                "sections": sections,
                "has_lyrics": has_lyrics,
                "gamaka_annotations": gamakas,
                "tags": _as_list(row.get("tags")),
                "source": row.get("source"),
                "license": row.get("license"),
            }
        )

    result = pd.DataFrame.from_records(records)
    log.info(STAGE, "output_rows", f"{len(result)} records normalised",
             n_rows=len(result))
    return result


def trinity_subset(frame: pd.DataFrame, log: QualityLog) -> pd.DataFrame:
    """The Trinity-only dataset (PRD section 10 deliverable)."""
    subset = frame.loc[frame["composer_group"] == config.GROUP_TRINITY].copy()
    by_composer = subset["composer"].value_counts().to_dict()
    log.info(
        STAGE, "trinity_subset",
        f"{len(subset)} Trinity compositions: "
        + ", ".join(f"{name} {count}" for name, count in sorted(by_composer.items())),
        n_rows=len(subset), by_composer=by_composer,
    )
    return subset.reset_index(drop=True)
