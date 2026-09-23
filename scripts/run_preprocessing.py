#!/usr/bin/env python
"""Command-line entry point for the Swaraga preprocessing pipeline.

Usage::

    python scripts/run_preprocessing.py
    python scripts/run_preprocessing.py --source path/to/other.parquet --seed 7
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from swaraga import config              # noqa: E402
from swaraga.pipeline import run        # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean, normalise, validate and split the Carnatic composition dataset.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=config.SOURCE_PARQUET,
        help="raw parquet to ingest (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=config.SPLIT_SEED,
        help="random seed for the train/val/test split (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run(source=args.source, seed=args.seed)

    stats = result.statistics
    severities = result.log.counts_by_severity()

    print("Preprocessing complete.")
    print(f"  compositions      : {stats['n_compositions']} "
          f"(from {len(result.raw)} raw records)")
    print(f"  unique composers  : {stats['n_unique_composers']}")
    print(f"  Trinity           : {stats['n_trinity_compositions']}")
    print(f"  unique ragas      : {stats['n_unique_ragas']}")
    print(f"  unique talas      : {stats['n_unique_talas']}")
    print(f"  mean seq length   : {stats['sequence_length']['mean']}")
    print(f"  swara vocabulary  : {len(stats['swara_vocabulary'])}")
    print(f"  splits            : "
          f"{len(result.splits['train'])} train / "
          f"{len(result.splits['val'])} val / "
          f"{len(result.splits['test'])} test")
    if result.trinity_splits:
        print(f"  Trinity splits    : "
              f"{len(result.trinity_splits['train'])} train / "
              f"{len(result.trinity_splits['val'])} val / "
              f"{len(result.trinity_splits['test'])} test")
    print(f"  quality events    : {severities['error']} errors, "
          f"{severities['warning']} warnings, {severities['info']} info")
    print()
    print("Artefacts:")
    for path in (
        config.CLEANED_DATASET, config.NORMALIZED_DATASET, config.TRINITY_DATASET,
        config.TRAIN_JSONL, config.VAL_JSONL, config.TEST_JSONL,
        config.STATISTICS_JSON, config.STATISTICS_MD,
        config.QUALITY_LOG_MD, config.QUALITY_LOG_JSONL,
    ):
        print(f"  {path.relative_to(config.PROJECT_ROOT)}")

    return 1 if severities["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
