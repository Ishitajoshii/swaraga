"""Dataset validation and statistics (PRD section 6).

Produces the numbers needed to judge whether the Trinity classes are
represented well enough to train on, as JSON plus a Markdown report.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from . import config
from .quality_log import QualityLog

STAGE = "validate"


def compute_statistics(frame: pd.DataFrame, log: QualityLog,
                       label: str = "full") -> Dict[str, Any]:
    """Compute the full statistics block for a normalised dataset.

    ``label`` tags the dataset-level events so that statistics for the full
    dataset and for the Trinity subset stay distinguishable in the log.
    """
    lengths = frame["sequence_length"]
    swaras = frame["n_swaras"]

    trinity = frame.loc[frame["composer_group"] == config.GROUP_TRINITY]

    vocabulary = Counter()
    for sequence in frame["swara_sequence"]:
        vocabulary.update(sequence)

    token_vocabulary = Counter()
    for sequence in frame["token_sequence"]:
        token_vocabulary.update(sequence)

    stats: Dict[str, Any] = {
        "n_compositions": int(len(frame)),
        "n_unique_composers": int(frame["composer"].nunique()),
        "n_trinity_compositions": int(len(trinity)),
        "n_unique_ragas": int(frame["raga"].nunique()),
        "n_unique_talas": int(frame["tala"].nunique()),
        "n_unique_melakartas": int(frame["mela"].nunique()),
        "sequence_length": {
            "mean": round(float(lengths.mean()), 2),
            "median": float(lengths.median()),
            "min": int(lengths.min()),
            "max": int(lengths.max()),
            "std": round(float(lengths.std(ddof=0)), 2),
            "total_tokens": int(lengths.sum()),
        },
        "swara_count": {
            "mean": round(float(swaras.mean()), 2),
            "min": int(swaras.min()),
            "max": int(swaras.max()),
            "total": int(swaras.sum()),
        },
        "missing_values": _missing_values(frame),
        "duplicate_counts": {
            "duplicate_ids": int(frame["id"].duplicated().sum()),
            "duplicate_titles": int(frame["title"].duplicated().sum()),
            "duplicate_swara_sequences": int(
                pd.Series([tuple(s) for s in frame["swara_sequence"]]).duplicated().sum()
            ),
        },
        "distribution_by_composer": _counts(frame, "composer"),
        "distribution_by_composer_group": _counts(frame, "composer_group"),
        "distribution_by_raga": _counts(frame, "raga"),
        "distribution_by_tala": _counts(frame, "tala"),
        "distribution_by_melakarta": {
            str(mela): int(count)
            for mela, count in frame["mela"].value_counts().sort_index().items()
        },
        "distribution_by_length_flag": _counts(frame, "length_flag"),
        "distribution_by_composer_certainty": _counts(frame, "composer_certainty"),
        "trinity_by_composer": _counts(trinity, "composer") if len(trinity) else {},
        "swara_vocabulary": dict(sorted(vocabulary.items())),
        "token_vocabulary_size": len(token_vocabulary),
        "token_vocabulary": dict(sorted(token_vocabulary.items())),
        "lyrics_coverage": {
            "compositions_with_lyrics": int(frame["has_lyrics"].sum()),
            "compositions_without_lyrics": int((~frame["has_lyrics"]).sum()),
        },
        "license_distribution": _counts(frame, "license"),
    }

    log.info(STAGE, "statistics_computed",
             f"[{label}] {stats['n_compositions']} compositions, "
             f"{stats['n_unique_composers']} composers, "
             f"{stats['n_trinity_compositions']} Trinity, "
             f"{stats['n_unique_ragas']} ragas, {stats['n_unique_talas']} talas")

    _warn_on_thin_classes(stats, log, label)
    return stats


def _counts(frame: pd.DataFrame, column: str) -> Dict[str, int]:
    if column not in frame.columns or frame.empty:
        return {}
    return {str(key): int(value) for key, value in frame[column].value_counts().items()}


def _missing_values(frame: pd.DataFrame) -> Dict[str, int]:
    """Per-column count of nulls and empty strings / lists."""
    missing: Dict[str, int] = {}
    for column in frame.columns:
        series = frame[column]
        count = 0
        for value in series:
            if value is None:
                count += 1
            elif isinstance(value, float) and pd.isna(value):
                count += 1
            elif isinstance(value, (str, list, dict)) and len(value) == 0:
                count += 1
        if count:
            missing[column] = count
    return missing


def _warn_on_thin_classes(stats: Dict[str, Any], log: QualityLog, label: str) -> None:
    """Flag conditioning classes too thin to learn from."""
    for composer, count in stats["distribution_by_composer"].items():
        if count < 3:
            log.warning(STAGE, "sparse_composer_class",
                        f"[{label}] composer {composer!r} has only {count} composition(s); "
                        "too few to condition on reliably",
                        composer=composer, n=count)

    singleton_ragas = [r for r, c in stats["distribution_by_raga"].items() if c == 1]
    if singleton_ragas:
        log.warning(STAGE, "sparse_raga_classes",
                    f"[{label}] {len(singleton_ragas)} of {stats['n_unique_ragas']} ragas appear "
                    "exactly once; raga conditioning cannot generalise from one example",
                    ragas=sorted(singleton_ragas))

    if stats["n_compositions"] < 100:
        log.warning(STAGE, "dataset_small",
                    f"[{label}] {stats['n_compositions']} compositions is far below what a "
                    "composer-conditioned generator needs; treat any trained model "
                    "as a pipeline smoke test rather than a musical result",
                    n=stats["n_compositions"])


def write_statistics(stats: Dict[str, Any], json_path: Path, md_path: Path) -> None:
    """Write the statistics as JSON and as a readable Markdown report."""
    json_path = Path(json_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    lines: List[str] = [
        "# Dataset statistics",
        "",
        "Computed from `data/processed/normalized_dataset.parquet`.",
        "",
        "## Headline",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Compositions | {stats['n_compositions']} |",
        f"| Unique composers | {stats['n_unique_composers']} |",
        f"| Trinity compositions | {stats['n_trinity_compositions']} |",
        f"| Unique ragas | {stats['n_unique_ragas']} |",
        f"| Unique talas | {stats['n_unique_talas']} |",
        f"| Unique melakartas | {stats['n_unique_melakartas']} |",
        f"| Mean sequence length | {stats['sequence_length']['mean']} |",
        f"| Median sequence length | {stats['sequence_length']['median']} |",
        f"| Shortest / longest | {stats['sequence_length']['min']} / "
        f"{stats['sequence_length']['max']} |",
        f"| Total swara tokens | {stats['swara_count']['total']} |",
        f"| Swara vocabulary size | {len(stats['swara_vocabulary'])} |",
        f"| Full token vocabulary size | {stats['token_vocabulary_size']} |",
        "",
    ]

    lines += _table("Distribution by composer group", stats["distribution_by_composer_group"],
                    "Group")
    lines += _table("Distribution by composer", stats["distribution_by_composer"], "Composer")
    lines += _table("Trinity breakdown", stats["trinity_by_composer"], "Composer")
    lines += _table("Distribution by tala", stats["distribution_by_tala"], "Tala")
    lines += _table("Distribution by raga", stats["distribution_by_raga"], "Raga")
    lines += _table("Composer attribution certainty",
                    stats["distribution_by_composer_certainty"], "Certainty")
    lines += _table("Sequence-length flags", stats["distribution_by_length_flag"], "Flag")
    lines += _table("Swara vocabulary", stats["swara_vocabulary"], "Token")

    duplicates = stats["duplicate_counts"]
    lines += [
        "## Duplicates",
        "",
        "| Check | Count |",
        "| --- | ---: |",
        f"| Duplicate ids | {duplicates['duplicate_ids']} |",
        f"| Duplicate titles | {duplicates['duplicate_titles']} |",
        f"| Duplicate swara sequences | {duplicates['duplicate_swara_sequences']} |",
        "",
    ]

    missing = stats["missing_values"]
    lines += ["## Missing values", ""]
    if missing:
        lines += ["| Column | Missing / empty |", "| --- | ---: |"]
        lines += [f"| `{column}` | {count} |" for column, count in sorted(missing.items())]
    else:
        lines.append("No missing or empty values in any column.")
    lines.append("")

    lyrics = stats["lyrics_coverage"]
    lines += [
        "## Lyrics coverage",
        "",
        f"- With lyrics on at least one section: **{lyrics['compositions_with_lyrics']}**",
        f"- Without any lyrics: **{lyrics['compositions_without_lyrics']}**",
        "",
    ]

    md_path = Path(md_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _table(title: str, mapping: Dict[str, int], key_header: str) -> List[str]:
    if not mapping:
        return []
    lines = [f"## {title}", "", f"| {key_header} | Count |", "| --- | ---: |"]
    lines += [f"| {key} | {value} |" for key, value in
              sorted(mapping.items(), key=lambda kv: (-kv[1], kv[0]))]
    lines.append("")
    return lines
