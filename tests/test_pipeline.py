"""End-to-end pipeline behaviour, including the anti-leakage guarantee."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from swaraga import config
from swaraga.pipeline import run
from swaraga.split import TRAINING_FIELDS, split_dataset
from swaraga.quality_log import QualityLog


@pytest.fixture(scope="module")
def result():
    return run()


def test_pipeline_produces_every_deliverable(result) -> None:
    for path in (
        config.RAW_DATASET,
        config.CLEANED_DATASET,
        config.NORMALIZED_DATASET,
        config.TRINITY_DATASET,
        config.TRAIN_JSONL,
        config.VAL_JSONL,
        config.TEST_JSONL,
        config.COMPOSER_DICT,
        config.RAGA_DICT,
        config.TALA_DICT,
        config.STATISTICS_JSON,
        config.STATISTICS_MD,
        config.QUALITY_LOG_MD,
        config.QUALITY_LOG_JSONL,
    ):
        assert path.exists(), f"missing deliverable: {path}"


def test_no_records_were_silently_lost(result) -> None:
    """Any drop must be accounted for by a logged reason."""
    dropped = len(result.raw) - len(result.normalized)
    logged = sum(1 for e in result.log.events if e.code == "record_dropped")
    assert dropped == logged


def test_pipeline_reports_no_errors(result) -> None:
    errors = [e for e in result.log.events if e.severity == "error"]
    assert errors == [], [e.message for e in errors]


def test_splits_partition_the_dataset(result) -> None:
    total = sum(len(part) for part in result.splits.values())
    assert total == len(result.normalized)


def test_no_composition_spans_two_splits(result) -> None:
    ids = {name: set(part["id"]) for name, part in result.splits.items()}
    assert not ids["train"] & ids["val"]
    assert not ids["train"] & ids["test"]
    assert not ids["val"] & ids["test"]


def test_no_section_of_a_composition_leaks_across_splits(result) -> None:
    """PRD 7: fragments of one composition must not span splits.

    Sections travel inside their composition's row, so checking that every
    (composition id, section name) pair occurs in exactly one split proves it.
    """
    seen: dict[tuple[str, str], str] = {}
    for name, part in result.splits.items():
        for record_id, sections in zip(part["id"], part["sections"]):
            for sec in sections:
                key = (record_id, sec["name"])
                assert key not in seen or seen[key] == name
                seen[key] = name


def test_split_ratios_match_the_prd(result) -> None:
    total = len(result.normalized)
    assert len(result.splits["train"]) == round(total * config.SPLIT_RATIOS["train"])
    assert len(result.splits["val"]) == round(total * config.SPLIT_RATIOS["val"])
    assert len(result.splits["test"]) == round(total * config.SPLIT_RATIOS["test"])


def test_trinity_appears_in_every_split(result) -> None:
    for name, part in result.splits.items():
        trinity = (part["composer_group"] == config.GROUP_TRINITY).sum()
        assert trinity > 0, f"no Trinity composition in {name}"


def test_split_is_deterministic(result) -> None:
    log = QualityLog()
    again = split_dataset(result.normalized, log, seed=config.SPLIT_SEED, label="repeat")
    for name in ("train", "val", "test"):
        assert list(again[name]["id"]) == list(result.splits[name]["id"])


def test_training_records_carry_the_prd_schema(result) -> None:
    rows = [json.loads(line) for line in
            config.TRAIN_JSONL.read_text(encoding="utf-8").splitlines()]
    assert rows
    for row in rows:
        for field in TRAINING_FIELDS:
            assert field in row, f"{field} missing from training record"
        assert row["composer_group"] in config.COMPOSER_GROUPS
        assert isinstance(row["swara_sequence"], list)
        assert row["swara_sequence"]


def test_trinity_dataset_holds_only_trinity(result) -> None:
    assert set(result.trinity["composer_group"]) == {config.GROUP_TRINITY}
    assert set(result.trinity["composer"]) <= {
        "Tyagaraja", "Muthuswami Dikshitar", "Syama Sastri",
    }


def test_composer_originals_are_retained(result) -> None:
    """PRD 4: the original value survives normalisation."""
    assert "composer_raw" in result.normalized.columns
    raw_names = set(result.raw["composer"])
    assert set(result.normalized["composer_raw"]) <= raw_names


def test_thyagaraja_was_normalised(result) -> None:
    assert "Thyagaraja" in set(result.raw["composer"])
    assert "Thyagaraja" not in set(result.normalized["composer"])
    assert "Tyagaraja" in set(result.normalized["composer"])


def test_every_swara_token_is_legal(result) -> None:
    legal_special = {config.REST}
    for sequence in result.normalized["swara_sequence"]:
        for token in sequence:
            if token in legal_special:
                continue
            base = token.rstrip("'.")
            assert base in {
                "S", "P",
                "R1", "R2", "R3", "G1", "G2", "G3",
                "M1", "M2", "D1", "D2", "D3", "N1", "N2", "N3",
            }, f"illegal token {token!r}"


def test_resolved_swaras_belong_to_the_parent_mela(result) -> None:
    """Every variant used must be one the composition's melakarta allows."""
    from swaraga.melakarta import full_scale_for_mela

    for _, row in result.normalized.iterrows():
        allowed = set(full_scale_for_mela(row["mela"]))
        for token in row["swara_sequence"]:
            if token == config.REST:
                continue
            assert token.rstrip("'.") in allowed


def test_rests_are_preserved_from_the_source_notation(result) -> None:
    """The raw ``tokens`` column dropped all rests; the rebuilt one must not."""
    total_rests = sum(
        sequence.count(config.REST) for sequence in result.normalized["swara_sequence"]
    )
    assert total_rests == int(result.normalized["n_rests"].sum())
    assert total_rests > 0


def test_lyrics_are_preserved(result) -> None:
    """PRD 3: preserve lyrics rather than deleting them."""
    with_lyrics = [
        sec["lyrics"]
        for sections in result.normalized["sections"]
        for sec in sections
        if sec["lyrics"]
    ]
    assert with_lyrics


def test_statistics_agree_with_the_dataset(result) -> None:
    stats = result.statistics
    assert stats["n_compositions"] == len(result.normalized)
    assert stats["n_unique_composers"] == result.normalized["composer"].nunique()
    assert stats["n_trinity_compositions"] == len(result.trinity)


def test_quality_log_is_valid_jsonl(result) -> None:
    lines = config.QUALITY_LOG_JSONL.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(result.log.events)
    for line in lines:
        event = json.loads(line)
        assert event["severity"] in ("info", "warning", "error")
        assert event["code"]
