"""Controlled-vocabulary normalisation for composer, raga and tala."""

from __future__ import annotations

import pytest

from swaraga import config
from swaraga.normalizers import ComposerNormalizer, RagaNormalizer, TalaNormalizer
from swaraga.period import parse_period


@pytest.fixture(scope="module")
def composers() -> ComposerNormalizer:
    return ComposerNormalizer()


@pytest.fixture(scope="module")
def ragas() -> RagaNormalizer:
    return RagaNormalizer()


@pytest.fixture(scope="module")
def talas() -> TalaNormalizer:
    return TalaNormalizer()


# --- composer ---------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Thyagaraja", "Tyagaraja"),
        ("Tyagaraja Swami", "Tyagaraja"),
        ("Sri Tyagaraja", "Tyagaraja"),
        ("Muthuswamy Dikshitar", "Muthuswami Dikshitar"),
        ("Dikshitar", "Muthuswami Dikshitar"),
        ("Shyama Sastri", "Syama Sastri"),
        ("Syama Sastrigal", "Syama Sastri"),
    ],
)
def test_trinity_aliases_map_to_canonical(composers, raw, expected) -> None:
    result = composers.normalize(raw)
    assert result.composer == expected
    assert result.composer_group == config.GROUP_TRINITY
    assert result.composer_raw == raw          # traceability (PRD 4)


def test_exactly_three_trinity_members(composers) -> None:
    assert sorted(composers.trinity_members) == [
        "Muthuswami Dikshitar", "Syama Sastri", "Tyagaraja",
    ]


def test_case_and_spacing_are_ignored_in_lookup(composers) -> None:
    assert composers.normalize("  muthuswamy   DIKSHITAR ").composer == "Muthuswami Dikshitar"


def test_unknown_composer_is_kept_not_dropped_and_not_trinity(composers) -> None:
    result = composers.normalize("Some Unlisted Vaggeyakara")
    assert result.composer == "Some Unlisted Vaggeyakara"
    assert result.composer_group == config.GROUP_UNKNOWN
    assert result.matched is False


def test_lookalike_name_is_not_promoted_to_trinity(composers) -> None:
    """PRD 2: Trinity membership must never follow from spelling similarity."""
    result = composers.normalize("Tyagaraja Bhagavatar of Harikesanallur")
    assert result.composer_group != config.GROUP_TRINITY
    assert result.matched is False


def test_hedged_attribution_keeps_the_hedge(composers) -> None:
    result = composers.normalize("Purandaradasa (attributed)")
    assert result.composer == "Purandaradasa"
    assert result.certainty == "attributed"
    assert result.composer_raw == "Purandaradasa (attributed)"


def test_school_attribution_does_not_become_the_composer(composers) -> None:
    result = composers.normalize("Traditional (attributed to Purandaradasa school)")
    assert result.composer == "Traditional"
    assert result.composer_group == config.GROUP_UNKNOWN
    assert result.attribution_note == "attributed to Purandaradasa school"


def test_empty_composer(composers) -> None:
    result = composers.normalize("")
    assert result.matched is False
    assert "composer_missing" in result.issues


# --- raga -------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Hamsadhvani", "Hamsadhwani"),
        ("Hamsadhwani", "Hamsadhwani"),
        ("Thodi", "Todi"),
        ("Sankarabharanam", "Shankarabharanam"),
        ("Shuddha Saveri", "Suddha Saveri"),
        ("Ritigowla", "Reethigowla"),
    ],
)
def test_raga_aliases(ragas, raw, expected) -> None:
    result = ragas.normalize(raw)
    assert result.raga == expected
    assert result.raga_raw == raw


def test_raga_carries_parent_mela(ragas) -> None:
    assert ragas.normalize("Kalyani").mela == 65
    assert ragas.normalize("Todi").mela == 8


def test_bhairavi_carries_its_bhashanga_caveat(ragas) -> None:
    assert "bhashanga" in (ragas.normalize("Bhairavi").notes or "").lower()


def test_unknown_raga_is_kept(ragas) -> None:
    result = ragas.normalize("Ranjani")
    assert result.raga == "Ranjani"
    assert result.matched is False


# --- tala -------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected,aksharas",
    [
        ("Adi", "Adi", 8),
        ("Aadi", "Adi", 8),
        ("Roopaka", "Rupaka", 6),
        ("Mishra Chapu", "Misra Chapu", 7),
        ("Ata", "Khanda Ata", 14),
        ("Chaturashra Dhruvam", "Chaturasra Dhruva", 14),
    ],
)
def test_tala_aliases(talas, raw, expected, aksharas) -> None:
    result = talas.normalize(raw)
    assert result.tala == expected
    assert result.aksharas == aksharas


def test_free_alapana_is_marked_unmetered(talas) -> None:
    result = talas.normalize("Free (Alapana)", 0)
    assert result.metered is False
    assert result.aksharas == 0


def test_akshara_disagreement_is_flagged(talas) -> None:
    result = talas.normalize("Adi", 7)
    assert any("tala_aksharas_mismatch" in issue for issue in result.issues)
    assert result.aksharas == 8      # the dictionary wins


def test_matching_akshara_count_is_silent(talas) -> None:
    result = talas.normalize("Adi", 8)
    assert not any("tala_aksharas_mismatch" in issue for issue in result.issues)


# --- period -----------------------------------------------------------------

def test_period_life_years() -> None:
    result = parse_period("18th century (1775–1835)")
    assert (result.birth_year, result.death_year) == (1775, 1835)
    assert result.century == "18th"


def test_period_century_range() -> None:
    result = parse_period("18th–19th century (1762–1827)")
    assert result.century == "18th-19th"
    assert (result.birth_year, result.death_year) == (1762, 1827)


def test_period_without_dates() -> None:
    result = parse_period("Classical")
    assert result.birth_year is None
    assert "period_undated" in result.issues
