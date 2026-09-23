"""Train / validation / test splitting (PRD section 7).

The split unit is the **whole composition**.  A composition's sections never
land in different splits, so no fragment of a training composition can appear
in validation or test.

Splitting is stratified by ``composer_group`` and, within a group, ordered so
that consecutive picks come from different composers.  That gives the holdout
sets as much composer variety as a dataset this small allows.
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import pandas as pd

from . import config
from .quality_log import QualityLog

STAGE = "split"

#: Fields written to the JSONL training files (PRD section 8).
TRAINING_FIELDS = (
    "id",
    "composer",
    "composer_group",
    "raga",
    "tala",
    "swara_sequence",
)

#: Extra fields kept alongside them; useful for conditioning experiments and
#: for tracing a generated sample back to its source.
CONTEXT_FIELDS = (
    "title",
    "mela",
    "mela_name",
    "raga_scale",
    "tala_aksharas",
    "is_metered",
    "speed",
    "token_sequence",
    "sequence_length",
    "n_swaras",
    "has_lyrics",
    "composer_certainty",
    "length_flag",
    "license",
)


def _interleave_by_composer(frame: pd.DataFrame, rng: random.Random) -> List[int]:
    """Order row positions so that consecutive picks change composer.

    Round-robin over composers, each composer's own compositions shuffled.
    Taking the first *k* of this ordering therefore spreads a small holdout
    across as many composers as possible.
    """
    by_composer: Dict[str, List[int]] = defaultdict(list)
    for position, composer in enumerate(frame["composer"]):
        by_composer[composer].append(position)

    for positions in by_composer.values():
        rng.shuffle(positions)

    # Rarest composers first, so a single-composition composer is not always
    # the one squeezed out of the holdout.
    queues = sorted(by_composer.items(), key=lambda item: (len(item[1]), item[0]))
    ordered: List[int] = []
    while any(positions for _, positions in queues):
        for _, positions in queues:
            if positions:
                ordered.append(positions.pop())
    return ordered


def _allocate_holdouts(sizes: Dict[str, int]) -> Dict[str, Tuple[int, int, int]]:
    """Decide (train, val, test) counts per stratum.

    The PRD's 80/10/10 is a whole-dataset target, so the holdout sizes are
    computed globally and then handed out to strata, rather than rounding
    inside each stratum (which inflates the holdout when there are several
    small strata - with three strata and twenty records, per-stratum rounding
    yields 70/15/15).

    Slots go to the largest strata first, with Trinity given priority so the
    class the PRD cares about evaluating is present in every split.  A
    stratum too small to give up a record keeps all of its rows in train.
    """
    total = sum(sizes.values())
    n_val = round(total * config.SPLIT_RATIOS["val"])
    n_test = round(total * config.SPLIT_RATIOS["test"])

    eligible = [
        group for group, size in sizes.items()
        if size >= config.MIN_STRATUM_FOR_HOLDOUT
    ]
    # Trinity first, then largest stratum first, then alphabetical for stability.
    eligible.sort(key=lambda group: (group != config.GROUP_TRINITY, -sizes[group], group))

    allocated = {group: [size, 0, 0] for group, size in sizes.items()}

    def hand_out(slots: int, index: int) -> None:
        """Deal ``slots`` holdout places round-robin over the eligible strata."""
        if not eligible:
            return
        position = 0
        while slots > 0:
            group = eligible[position % len(eligible)]
            # Never take a stratum's last training row.
            if allocated[group][0] > 1:
                allocated[group][index] += 1
                allocated[group][0] -= 1
                slots -= 1
            position += 1
            if position > len(eligible) * total:  # nothing left to give
                break

    hand_out(n_val, 1)
    hand_out(n_test, 2)

    return {group: tuple(counts) for group, counts in allocated.items()}


def split_dataset(
    frame: pd.DataFrame,
    log: QualityLog,
    seed: int = config.SPLIT_SEED,
    label: str = "full",
) -> Dict[str, pd.DataFrame]:
    """Split a normalised dataset into train / val / test."""
    rng = random.Random(seed)
    assignments: Dict[str, str] = {}

    sizes = {
        group: int((frame["composer_group"] == group).sum())
        for group in sorted(frame["composer_group"].unique())
    }
    allocation = _allocate_holdouts(sizes)

    for group in sorted(sizes):
        stratum = frame.loc[frame["composer_group"] == group].reset_index(drop=True)
        order = _interleave_by_composer(stratum, rng)
        n_train, n_val, n_test = allocation[group]

        # Holdouts are taken from the front of the interleaved ordering.
        val_positions = order[:n_val]
        test_positions = order[n_val:n_val + n_test]
        train_positions = order[n_val + n_test:]

        for position in val_positions:
            assignments[stratum.at[position, "id"]] = "val"
        for position in test_positions:
            assignments[stratum.at[position, "id"]] = "test"
        for position in train_positions:
            assignments[stratum.at[position, "id"]] = "train"

        log.info(
            STAGE, "stratum_allocated",
            f"[{label}] {group}: {n_train} train / {n_val} val / {n_test} test "
            f"from {len(stratum)} compositions",
            group=group, n_train=n_train, n_val=n_val, n_test=n_test,
        )
        if n_val == 0 and n_test == 0:
            log.warning(
                STAGE, "stratum_train_only",
                f"[{label}] {group} ({len(stratum)} compositions) received no "
                "holdout slots, so it is absent from val and test; at this dataset "
                "size the 80/10/10 target cannot cover every group",
                group=group, n=len(stratum),
            )

    splits = {
        name: frame.loc[frame["id"].map(assignments) == name].reset_index(drop=True)
        for name in ("train", "val", "test")
    }

    _verify_no_leakage(splits, log, label)
    _report_composition(splits, log, label)
    return splits


def _verify_no_leakage(splits: Dict[str, pd.DataFrame], log: QualityLog, label: str) -> None:
    """Assert that no composition, and no swara sequence, spans two splits."""
    ids = {name: set(part["id"]) for name, part in splits.items()}
    for first, second in (("train", "val"), ("train", "test"), ("val", "test")):
        overlap = ids[first] & ids[second]
        if overlap:
            log.error(STAGE, "split_leakage",
                      f"[{label}] {len(overlap)} composition(s) appear in both "
                      f"{first} and {second}: {sorted(overlap)}",
                      overlap=sorted(overlap))
            raise AssertionError(f"split leakage between {first} and {second}: {overlap}")

    sequences: Dict[Tuple[str, ...], str] = {}
    for name, part in splits.items():
        for record_id, sequence in zip(part["id"], part["swara_sequence"]):
            key = tuple(sequence)
            if key in sequences and sequences[key] != name:
                log.warning(
                    STAGE, "identical_sequence_across_splits",
                    f"[{label}] {record_id} has a swara sequence identical to a "
                    f"composition in {sequences[key]}",
                    record_id=record_id,
                )
            sequences.setdefault(key, name)

    log.info(STAGE, "leakage_check_passed",
             f"[{label}] no composition appears in more than one split")


def _report_composition(splits: Dict[str, pd.DataFrame], log: QualityLog, label: str) -> None:
    """Log what each split actually ended up containing."""
    total = sum(len(part) for part in splits.values())
    for name, part in splits.items():
        share = (len(part) / total * 100) if total else 0.0
        composers = ", ".join(sorted(part["composer"].unique())) or "-"
        log.info(
            STAGE, "split_composition",
            f"[{label}] {name}: {len(part)} compositions ({share:.0f}%); "
            f"composers: {composers}",
            split=name, n=len(part), share=round(share, 1),
            composers=sorted(part["composer"].unique()),
            groups=sorted(part["composer_group"].unique()),
        )

    trinity_present = {
        name: int((part["composer_group"] == config.GROUP_TRINITY).sum())
        for name, part in splits.items()
    }
    missing = [name for name, count in trinity_present.items() if count == 0]
    if missing:
        log.warning(STAGE, "trinity_absent_from_split",
                    f"[{label}] no Trinity composition in: {', '.join(missing)}",
                    splits=missing)


def to_training_record(row: pd.Series) -> Dict[str, Any]:
    """Project one normalised row onto the training-example schema."""
    record = {field: _jsonable(row[field]) for field in TRAINING_FIELDS}
    record.update({field: _jsonable(row[field]) for field in CONTEXT_FIELDS
                   if field in row.index})
    return record


def _jsonable(value: Any) -> Any:
    """Convert numpy / pandas scalars and arrays into plain JSON types."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def write_jsonl(frame: pd.DataFrame, path: Path, log: QualityLog) -> None:
    """Write one split as JSON Lines."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for _, row in frame.iterrows():
            handle.write(json.dumps(to_training_record(row), ensure_ascii=False) + "\n")
    log.info(STAGE, "jsonl_written", f"{len(frame)} records -> {path.name}",
             path=str(path), n_rows=len(frame))


def write_splits(splits: Dict[str, pd.DataFrame], paths: Dict[str, Path],
                 log: QualityLog) -> None:
    """Write train / val / test JSONL files."""
    for name, path in paths.items():
        write_jsonl(splits[name], path, log)
