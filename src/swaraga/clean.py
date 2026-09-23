"""Stage 1: raw_dataset.parquet -> cleaned_dataset.parquet (PRD section 3).

This stage is about *integrity*, not vocabulary:

- repair lossy-decode artefacts and strip formatting characters
- collapse whitespace in every text field
- drop exact duplicate records
- drop records whose musical notation is missing or unparseable
- validate the melakarta number and the raga's declared scale
- flag unusually short / long compositions

Composer, raga and tala strings are cleaned but *not* yet mapped to the
controlled vocabulary; that happens in :mod:`swaraga.normalize`.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from . import config
from .melakarta import MELAKARTA_NAMES, canonical_mela_name, validate_mela
from .notation import parse_sections, scale_letters
from .quality_log import QualityLog

STAGE = "clean"

#: Text columns that get the full character-level cleanup.
TEXT_COLUMNS = (
    "id", "title", "composer", "period", "raga", "mela_name", "tala",
    "speed", "arohanam", "avarohanam", "source", "license",
)

#: Columns holding JSON documents that need their inner strings cleaned too.
JSON_COLUMNS = ("sections_json", "gamaka_annotations_json")


def _clean_scalar(value: Any, record_id: Optional[str], column: str,
                  log: QualityLog) -> Any:
    """Clean one text cell and log whatever had to be repaired."""
    from .text_norm import clean_text

    if not isinstance(value, str):
        return value

    cleaned, issues = clean_text(value)
    for issue in issues:
        code, _, detail = issue.partition(":")
        log.add(
            STAGE,
            code,
            f"repaired {column}: {issue}",
            record_id=record_id,
            severity="warning" if code == "mojibake_repaired" else "info",
            field_name=column,
            before=value,
            after=cleaned,
            detail=detail or None,
        )
    return cleaned


def _clean_json_column(value: str, record_id: str, column: str,
                       log: QualityLog) -> str:
    """Re-serialise a JSON column with every inner string cleaned."""
    from .text_norm import clean_text

    try:
        payload = json.loads(value) if isinstance(value, str) else value
    except (TypeError, ValueError) as exc:
        log.error(
            STAGE,
            "json_unparseable",
            f"could not parse {column}: {exc}",
            record_id=record_id,
            field_name=column,
        )
        return value

    repairs: List[str] = []

    def walk(node: Any) -> Any:
        if isinstance(node, str):
            cleaned, issues = clean_text(node)
            repairs.extend(issues)
            return cleaned
        if isinstance(node, list):
            return [walk(item) for item in node]
        if isinstance(node, dict):
            return {key: walk(item) for key, item in node.items()}
        return node

    payload = walk(payload)

    for issue in sorted(set(repairs)):
        code = issue.partition(":")[0]
        log.add(
            STAGE,
            code,
            f"repaired {column}: {issue}",
            record_id=record_id,
            severity="warning" if code == "mojibake_repaired" else "info",
            field_name=column,
        )

    return json.dumps(payload, ensure_ascii=False)


def _validate_mela(row: pd.Series, log: QualityLog) -> Optional[int]:
    """Check the melakarta number and its declared name."""
    record_id = row["id"]
    raw_mela = row.get("mela")

    try:
        mela = validate_mela(int(raw_mela))
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        log.error(
            STAGE,
            "mela_invalid",
            f"unusable melakarta number {raw_mela!r}: {exc}",
            record_id=record_id,
            field_name="mela",
        )
        return None

    declared = canonical_mela_name(str(row.get("mela_name", "")))
    expected = MELAKARTA_NAMES[mela]
    if declared and declared != expected:
        log.warning(
            STAGE,
            "mela_name_mismatch",
            f"mela {mela} is {expected!r} but the record says {row['mela_name']!r}",
            record_id=record_id,
            field_name="mela_name",
            before=row["mela_name"],
            after=expected,
        )
    return mela


def _validate_scale_coverage(row: pd.Series, sections: List[dict],
                             log: QualityLog) -> None:
    """Flag notes used in the composition that the raga's scale does not list."""
    record_id = row["id"]
    allowed = scale_letters(row.get("arohanam", ""), row.get("avarohanam", ""))
    if not allowed:
        log.warning(
            STAGE,
            "scale_missing",
            "no arohanam / avarohanam to validate the notation against",
            record_id=record_id,
            field_name="arohanam",
        )
        return

    used: Dict[str, int] = {}
    for section in sections:
        for raw in (section.get("notation") or "").split():
            if raw in ("|", "||", ","):
                continue
            letter = raw[0].upper()
            if letter.isalpha():
                used[letter] = used.get(letter, 0) + 1

    outside = {letter: count for letter, count in used.items() if letter not in allowed}
    if outside:
        log.warning(
            STAGE,
            "note_outside_raga_scale",
            "notation uses swaras absent from the declared scale: "
            + ", ".join(f"{letter} x{count}" for letter, count in sorted(outside.items())),
            record_id=record_id,
            field_name="sections_json",
            outside=outside,
            allowed=sorted(allowed),
        )


def _flag_length_outliers(frame: pd.DataFrame, log: QualityLog) -> pd.DataFrame:
    """Add ``length_flag`` using a Tukey fence over swara counts."""
    lengths = frame["n_swaras"]
    q1, q3 = lengths.quantile(0.25), lengths.quantile(0.75)
    iqr = q3 - q1
    low_fence = q1 - config.IQR_FENCE * iqr
    high_fence = q3 + config.IQR_FENCE * iqr

    flags: List[str] = []
    for _, row in frame.iterrows():
        length = row["n_swaras"]
        if length < config.MIN_VALID_SWARAS:
            flag = "too_short"
        elif length < low_fence:
            flag = "unusually_short"
        elif length > high_fence:
            flag = "unusually_long"
        else:
            flag = "ok"
        flags.append(flag)

        if flag != "ok":
            log.warning(
                STAGE,
                f"length_{flag}",
                f"{length} swaras is outside the fence "
                f"[{low_fence:.1f}, {high_fence:.1f}]",
                record_id=row["id"],
                field_name="n_swaras",
                n_swaras=int(length),
                low_fence=float(low_fence),
                high_fence=float(high_fence),
            )

    frame = frame.copy()
    frame["length_flag"] = flags
    log.info(
        STAGE,
        "length_fence",
        f"swara-count fence [{low_fence:.1f}, {high_fence:.1f}] "
        f"from Q1={q1:.1f}, Q3={q3:.1f}",
        low_fence=float(low_fence),
        high_fence=float(high_fence),
    )
    return frame


def clean(frame: pd.DataFrame, log: QualityLog) -> pd.DataFrame:
    """Run the full cleaning stage."""
    frame = frame.copy()
    n_input = len(frame)
    log.info(STAGE, "input_rows", f"{n_input} raw records read", n_rows=n_input)

    # -- 1. character-level repair -----------------------------------------
    for column in TEXT_COLUMNS:
        if column not in frame.columns:
            log.error(STAGE, "column_missing", f"expected column {column!r} is absent",
                      field_name=column)
            continue
        frame[column] = [
            _clean_scalar(value, rid, column, log)
            for value, rid in zip(frame[column], frame.get("id", [None] * len(frame)))
        ]

    for column in JSON_COLUMNS:
        if column in frame.columns:
            frame[column] = [
                _clean_json_column(value, rid, column, log)
                for value, rid in zip(frame[column], frame["id"])
            ]

    # -- 2. exact duplicates ------------------------------------------------
    hashable = frame.astype(str)
    duplicate_mask = hashable.duplicated(keep="first")
    for record_id in frame.loc[duplicate_mask, "id"]:
        log.warning(STAGE, "duplicate_record_dropped",
                    "exact duplicate of an earlier record", record_id=record_id)
    frame = frame.loc[~duplicate_mask].copy()

    id_duplicate_mask = frame["id"].duplicated(keep="first")
    for record_id in frame.loc[id_duplicate_mask, "id"]:
        log.warning(STAGE, "duplicate_id_dropped",
                    "id already used by an earlier, non-identical record",
                    record_id=record_id)
    frame = frame.loc[~id_duplicate_mask].copy()

    # -- 3. notation validity ----------------------------------------------
    keep: List[bool] = []
    melas: List[Optional[int]] = []
    n_swaras: List[int] = []
    n_rests: List[int] = []
    n_sections: List[int] = []

    for _, row in frame.iterrows():
        record_id = row["id"]
        mela = _validate_mela(row, log)
        melas.append(mela)

        try:
            sections = json.loads(row["sections_json"])
        except (TypeError, ValueError) as exc:
            log.error(STAGE, "notation_unparseable",
                      f"sections_json could not be read: {exc}",
                      record_id=record_id, field_name="sections_json")
            keep.append(False)
            n_swaras.append(0)
            n_rests.append(0)
            n_sections.append(0)
            continue

        if not sections:
            log.error(STAGE, "notation_missing", "record has no sections",
                      record_id=record_id, field_name="sections_json")
            keep.append(False)
            n_swaras.append(0)
            n_rests.append(0)
            n_sections.append(0)
            continue

        if mela is None:
            keep.append(False)
            n_swaras.append(0)
            n_rests.append(0)
            n_sections.append(0)
            continue

        parsed = parse_sections(sections, mela)
        bad_tokens = [token for section in parsed for token in section.unparsed_tokens]
        if bad_tokens:
            log.error(STAGE, "notation_token_unparseable",
                      "unrecognised notation tokens: " + ", ".join(sorted(set(bad_tokens))),
                      record_id=record_id, field_name="sections_json",
                      tokens=sorted(set(bad_tokens)))

        swaras = sum(len(section.notes) for section in parsed)
        rests = sum(section.n_rests for section in parsed)

        if swaras == 0:
            log.error(STAGE, "notation_empty",
                      "notation contains no swaras", record_id=record_id,
                      field_name="sections_json")
            keep.append(False)
        else:
            keep.append(not bad_tokens)

        n_swaras.append(swaras)
        n_rests.append(rests)
        n_sections.append(len(parsed))

        _validate_scale_coverage(row, sections, log)

        # The source swara_count should agree with what the notation actually holds.
        declared = row.get("swara_count")
        if declared is not None and int(declared) != swaras:
            log.warning(
                STAGE, "swara_count_mismatch",
                f"swara_count says {int(declared)} but the notation has {swaras}",
                record_id=record_id, field_name="swara_count",
                before=int(declared), after=swaras,
            )

    frame["mela"] = melas
    frame["n_swaras"] = n_swaras
    frame["n_rests"] = n_rests
    frame["n_sections"] = n_sections

    dropped = frame.loc[[not k for k in keep], "id"].tolist()
    for record_id in dropped:
        log.error(STAGE, "record_dropped",
                  "dropped: missing or invalid musical notation", record_id=record_id)
    frame = frame.loc[keep].copy()

    # -- 4. length flags ----------------------------------------------------
    frame = _flag_length_outliers(frame, log)

    log.info(STAGE, "output_rows",
             f"{len(frame)} records survived cleaning (from {n_input})",
             n_rows=len(frame), n_dropped=n_input - len(frame))
    return frame.reset_index(drop=True)
