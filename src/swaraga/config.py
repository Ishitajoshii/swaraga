"""Paths, constants and tunable thresholds for the preprocessing pipeline."""

from __future__ import annotations

from pathlib import Path

# --- Layout -----------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_DIR = DATA_DIR / "raw"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
SPLITS_DIR = DATA_DIR / "splits"

SOURCE_PARQUET = PROJECT_ROOT / "train-00000-of-00001.parquet"

RAW_DATASET = RAW_DIR / "raw_dataset.parquet"
CLEANED_DATASET = INTERIM_DIR / "cleaned_dataset.parquet"
NORMALIZED_DATASET = PROCESSED_DIR / "normalized_dataset.parquet"
TRINITY_DATASET = PROCESSED_DIR / "trinity_dataset.parquet"

TRAIN_JSONL = SPLITS_DIR / "train.jsonl"
VAL_JSONL = SPLITS_DIR / "val.jsonl"
TEST_JSONL = SPLITS_DIR / "test.jsonl"

TRINITY_TRAIN_JSONL = SPLITS_DIR / "trinity_train.jsonl"
TRINITY_VAL_JSONL = SPLITS_DIR / "trinity_val.jsonl"
TRINITY_TEST_JSONL = SPLITS_DIR / "trinity_test.jsonl"

COMPOSER_DICT = CONFIG_DIR / "composer_normalization.json"
RAGA_DICT = CONFIG_DIR / "raga_normalization.json"
TALA_DICT = CONFIG_DIR / "tala_normalization.json"

STATISTICS_JSON = REPORTS_DIR / "dataset_statistics.json"
STATISTICS_MD = REPORTS_DIR / "dataset_report.md"
QUALITY_LOG_MD = REPORTS_DIR / "data_quality_log.md"
QUALITY_LOG_JSONL = REPORTS_DIR / "data_quality_log.jsonl"

ALL_OUTPUT_DIRS = (RAW_DIR, INTERIM_DIR, PROCESSED_DIR, SPLITS_DIR, REPORTS_DIR)

# --- Composer grouping (PRD section 2) --------------------------------------

GROUP_TRINITY = "Trinity"
GROUP_OTHER = "Other Known Composers"
GROUP_UNKNOWN = "Unknown / Unclassified"

COMPOSER_GROUPS = (GROUP_TRINITY, GROUP_OTHER, GROUP_UNKNOWN)

# --- Split configuration (PRD section 7) ------------------------------------

SPLIT_RATIOS = {"train": 0.80, "val": 0.10, "test": 0.10}
SPLIT_SEED = 42

# A stratum smaller than this cannot donate a row to val and test without
# starving train, so it is left entirely in train.
MIN_STRATUM_FOR_HOLDOUT = 4

# --- Sequence-length flagging (PRD section 3) -------------------------------

# Below this a composition carries too little musical content to train on.
MIN_VALID_SWARAS = 8
# Tukey fence multiplier used to flag unusually short / long compositions.
IQR_FENCE = 1.5

# --- Token vocabulary (PRD section 5) ---------------------------------------

BOS = "[BOS]"
EOS = "[EOS]"
REST = "[REST]"
OCTAVE_UP = "[OCTAVE_UP]"
OCTAVE_DOWN = "[OCTAVE_DOWN]"
BAR = "[BAR]"
SECTION_BAR = "[SBAR]"

SPECIAL_TOKENS = (BOS, EOS, REST, OCTAVE_UP, OCTAVE_DOWN, BAR, SECTION_BAR)

TALA_TOKEN_FMT = "[TALA:{tala}]"
SECTION_TOKEN_FMT = "[SECTION:{section}]"
