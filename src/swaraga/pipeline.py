"""End-to-end orchestration of the preprocessing pipeline.

    raw_dataset.parquet
        -> cleaned_dataset.parquet
        -> normalized_dataset.parquet
        -> train.jsonl / val.jsonl / test.jsonl

Plus the Trinity-filtered dataset and its own splits, the statistics report
and the data-quality log.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from . import config
from .clean import clean
from .normalize import normalize, trinity_subset
from .quality_log import QualityLog
from .split import split_dataset, write_splits
from .validate import compute_statistics, write_statistics

STAGE = "pipeline"


@dataclass
class PipelineResult:
    """Everything the pipeline produced, for programmatic use and for tests."""

    raw: pd.DataFrame
    cleaned: pd.DataFrame
    normalized: pd.DataFrame
    trinity: pd.DataFrame
    splits: Dict[str, pd.DataFrame]
    trinity_splits: Dict[str, pd.DataFrame]
    statistics: Dict[str, Any]
    trinity_statistics: Dict[str, Any]
    log: QualityLog


def ensure_directories() -> None:
    for directory in config.ALL_OUTPUT_DIRS:
        directory.mkdir(parents=True, exist_ok=True)


def stage_raw(source: Optional[Path] = None, log: Optional[QualityLog] = None) -> pd.DataFrame:
    """Copy the source parquet into ``data/raw`` and load it."""
    source = Path(source) if source else config.SOURCE_PARQUET

    if not source.exists():
        raise FileNotFoundError(f"source dataset not found: {source}")

    if source.resolve() != config.RAW_DATASET.resolve():
        config.RAW_DATASET.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, config.RAW_DATASET)

    frame = pd.read_parquet(config.RAW_DATASET)
    if log is not None:
        log.info(STAGE, "raw_loaded",
                 f"loaded {len(frame)} rows x {len(frame.columns)} columns from "
                 f"{source.name}",
                 n_rows=len(frame), n_columns=len(frame.columns),
                 columns=list(frame.columns))
    return frame


def run(source: Optional[Path] = None, seed: int = config.SPLIT_SEED) -> PipelineResult:
    """Run every stage and write every deliverable."""
    ensure_directories()
    log = QualityLog()

    # -- raw ----------------------------------------------------------------
    raw = stage_raw(source, log)

    # -- clean --------------------------------------------------------------
    cleaned = clean(raw, log)
    cleaned.to_parquet(config.CLEANED_DATASET, index=False)
    log.info(STAGE, "artifact_written", f"wrote {config.CLEANED_DATASET.name}",
             path=str(config.CLEANED_DATASET), n_rows=len(cleaned))

    # -- normalize ----------------------------------------------------------
    normalized = normalize(cleaned, log)
    _write_parquet(normalized, config.NORMALIZED_DATASET, log)

    trinity = trinity_subset(normalized, log)
    _write_parquet(trinity, config.TRINITY_DATASET, log)

    # -- validate -----------------------------------------------------------
    statistics = compute_statistics(normalized, log, label="full")
    write_statistics(statistics, config.STATISTICS_JSON, config.STATISTICS_MD)
    log.info(STAGE, "artifact_written", f"wrote {config.STATISTICS_JSON.name} and "
             f"{config.STATISTICS_MD.name}")

    trinity_statistics = (
        compute_statistics(trinity, log, label="trinity") if len(trinity) else {}
    )

    # -- split --------------------------------------------------------------
    splits = split_dataset(normalized, log, seed=seed, label="full")
    write_splits(
        splits,
        {"train": config.TRAIN_JSONL, "val": config.VAL_JSONL, "test": config.TEST_JSONL},
        log,
    )

    trinity_splits: Dict[str, pd.DataFrame] = {}
    if len(trinity) >= config.MIN_STRATUM_FOR_HOLDOUT:
        trinity_splits = split_dataset(trinity, log, seed=seed, label="trinity")
        write_splits(
            trinity_splits,
            {
                "train": config.TRINITY_TRAIN_JSONL,
                "val": config.TRINITY_VAL_JSONL,
                "test": config.TRINITY_TEST_JSONL,
            },
            log,
        )
    else:
        log.warning(STAGE, "trinity_splits_skipped",
                    f"only {len(trinity)} Trinity compositions; no separate "
                    "Trinity split was written")

    # -- quality log --------------------------------------------------------
    log.write_jsonl(config.QUALITY_LOG_JSONL)
    log.write_markdown(config.QUALITY_LOG_MD)

    return PipelineResult(
        raw=raw,
        cleaned=cleaned,
        normalized=normalized,
        trinity=trinity,
        splits=splits,
        trinity_splits=trinity_splits,
        statistics=statistics,
        trinity_statistics=trinity_statistics,
        log=log,
    )


def _write_parquet(frame: pd.DataFrame, path: Path, log: QualityLog) -> None:
    """Write a parquet file, logging the artefact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)
    log.info(STAGE, "artifact_written", f"wrote {path.name}",
             path=str(path), n_rows=len(frame))
