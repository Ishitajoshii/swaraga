"""Swaraga - Carnatic composition dataset cleanup and preprocessing.

Implements the pipeline described in ``preprocessing.md``:

    raw_dataset.parquet -> cleaned_dataset.parquet -> normalized_dataset.parquet
                        -> train.jsonl / val.jsonl / test.jsonl
"""

__version__ = "1.0.0"
