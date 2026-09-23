"""The melakarta derivation is the pipeline's authority for swara variants,
so it is pinned against ragas whose scales are independently well known."""

from __future__ import annotations

import pytest

from swaraga.melakarta import (
    MELAKARTA_NAMES,
    MelakartaError,
    canonical_mela_name,
    full_scale_for_mela,
    mela_name,
    swaras_for_mela,
    validate_mela,
)

# (mela, name, expected ascending scale) for every melakarta this dataset uses.
KNOWN_SCALES = [
    (8, "Hanumatodi", ["S", "R1", "G2", "M1", "P", "D1", "N2"]),
    (15, "Mayamalavagowla", ["S", "R1", "G3", "M1", "P", "D1", "N3"]),
    (20, "Natabhairavi", ["S", "R2", "G2", "M1", "P", "D1", "N2"]),
    (22, "Kharaharapriya", ["S", "R2", "G2", "M1", "P", "D2", "N2"]),
    (26, "Charukesi", ["S", "R2", "G3", "M1", "P", "D1", "N2"]),
    (28, "Harikambhoji", ["S", "R2", "G3", "M1", "P", "D2", "N2"]),
    (29, "Dheerasankarabharanam", ["S", "R2", "G3", "M1", "P", "D2", "N3"]),
    (36, "Chalanata", ["S", "R3", "G3", "M1", "P", "D3", "N3"]),
    (39, "Jhalavarali", ["S", "R1", "G1", "M2", "P", "D1", "N3"]),
    (65, "Mechakalyani", ["S", "R2", "G3", "M2", "P", "D2", "N3"]),
]


@pytest.mark.parametrize("mela,name,scale", KNOWN_SCALES)
def test_known_scales(mela: int, name: str, scale: list[str]) -> None:
    assert mela_name(mela) == name
    assert full_scale_for_mela(mela) == scale


def test_all_72_melakartas_are_named() -> None:
    assert sorted(MELAKARTA_NAMES) == list(range(1, 73))


def test_every_melakarta_resolves_to_seven_distinct_swaras() -> None:
    for mela in range(1, 73):
        scale = full_scale_for_mela(mela)
        assert len(scale) == 7
        assert len(set(scale)) == 7


def test_madhyama_switches_at_36() -> None:
    assert all(swaras_for_mela(m)["M"] == "M1" for m in range(1, 37))
    assert all(swaras_for_mela(m)["M"] == "M2" for m in range(37, 73))


def test_purvanga_repeats_every_six_melas() -> None:
    """Melas 1-36 and 37-72 share the same R/G sequence."""
    for mela in range(1, 37):
        lower, upper = swaras_for_mela(mela), swaras_for_mela(mela + 36)
        assert (lower["R"], lower["G"]) == (upper["R"], upper["G"])
        assert (lower["D"], lower["N"]) == (upper["D"], upper["N"])


@pytest.mark.parametrize("bad", [0, 73, -1, 100])
def test_out_of_range_melas_are_rejected(bad: int) -> None:
    with pytest.raises(MelakartaError):
        validate_mela(bad)


def test_short_form_names_resolve() -> None:
    assert canonical_mela_name("Shankarabharanam") == "Dheerasankarabharanam"
    assert canonical_mela_name("Todi") == "Hanumatodi"
    assert canonical_mela_name("Kalyani") == "Mechakalyani"


def test_unknown_name_is_returned_not_dropped() -> None:
    assert canonical_mela_name("Some Unlisted Raga") == "Some Unlisted Raga"
