"""The 72-melakarta system: canonical names and swara-variant resolution.

The raw dataset writes swaras with an inconsistent mix of case conventions
(``G`` vs ``g`` vs ``G+`` all appear for the same pitch class in different
rows), so letter case cannot be trusted to encode the variant.  The ``mela``
column, however, is a melakarta number, and a melakarta number determines
R/G/M/D/N variants exactly.  :func:`swaras_for_mela` is therefore the
authority used throughout the pipeline.
"""

from __future__ import annotations

from typing import Dict

MELAKARTA_NAMES: Dict[int, str] = {
    1: "Kanakangi", 2: "Ratnangi", 3: "Ganamurti", 4: "Vanaspati",
    5: "Manavati", 6: "Tanarupi", 7: "Senavati", 8: "Hanumatodi",
    9: "Dhenuka", 10: "Natakapriya", 11: "Kokilapriya", 12: "Rupavati",
    13: "Gayakapriya", 14: "Vakulabharanam", 15: "Mayamalavagowla",
    16: "Chakravakam", 17: "Suryakantam", 18: "Hatakambari",
    19: "Jhankaradhwani", 20: "Natabhairavi", 21: "Keeravani",
    22: "Kharaharapriya", 23: "Gourimanohari", 24: "Varunapriya",
    25: "Mararanjani", 26: "Charukesi", 27: "Sarasangi", 28: "Harikambhoji",
    29: "Dheerasankarabharanam", 30: "Naganandini", 31: "Yagapriya",
    32: "Ragavardhini", 33: "Gangeyabhushani", 34: "Vagadheeswari",
    35: "Shulini", 36: "Chalanata", 37: "Salagam", 38: "Jalarnavam",
    39: "Jhalavarali", 40: "Navaneetam", 41: "Pavani", 42: "Raghupriya",
    43: "Gavambodhi", 44: "Bhavapriya", 45: "Shubhapantuvarali",
    46: "Shadvidamargini", 47: "Suvarnangi", 48: "Divyamani",
    49: "Dhavalambari", 50: "Namanarayani", 51: "Kamavardhini",
    52: "Ramapriya", 53: "Gamanashrama", 54: "Vishwambhari",
    55: "Shyamalangi", 56: "Shanmukhapriya", 57: "Simhendramadhyamam",
    58: "Hemavati", 59: "Dharmavati", 60: "Neetimati", 61: "Kantamani",
    62: "Rishabhapriya", 63: "Latangi", 64: "Vachaspati", 65: "Mechakalyani",
    66: "Chitrambari", 67: "Sucharitra", 68: "Jyotiswarupini",
    69: "Dhatuvardhani", 70: "Nasikabhushani", 71: "Kosalam", 72: "Rasikapriya",
}

#: Short forms that appear in source data for a canonical melakarta name.
MELAKARTA_ALIASES: Dict[str, str] = {
    "shankarabharanam": "Dheerasankarabharanam",
    "sankarabharanam": "Dheerasankarabharanam",
    "dhirasankarabharanam": "Dheerasankarabharanam",
    "todi": "Hanumatodi",
    "thodi": "Hanumatodi",
    "hanumathodi": "Hanumatodi",
    "kalyani": "Mechakalyani",
    "varali": "Jhalavarali",
    "nata": "Chalanata",
    "nattai": "Chalanata",
    "mayamalavagoula": "Mayamalavagowla",
}

#: Purvanga (rishabha, gandhara) pairs, indexed by chakra position 0-5.
_PURVANGA = (("R1", "G1"), ("R1", "G2"), ("R1", "G3"),
             ("R2", "G2"), ("R2", "G3"), ("R3", "G3"))

#: Uttaranga (dhaivata, nishada) pairs, indexed by position-in-chakra 0-5.
_UTTARANGA = (("D1", "N1"), ("D1", "N2"), ("D1", "N3"),
              ("D2", "N2"), ("D2", "N3"), ("D3", "N3"))

#: Semitone offset above the tonic for every swara variant.
SWARA_SEMITONES: Dict[str, int] = {
    "S": 0,
    "R1": 1, "R2": 2, "R3": 3,
    "G1": 2, "G2": 3, "G3": 4,
    "M1": 5, "M2": 6,
    "P": 7,
    "D1": 8, "D2": 9, "D3": 10,
    "N1": 9, "N2": 10, "N3": 11,
}

#: Swaras that have no variants.
INVARIANT_SWARAS = ("S", "P")

#: Swaras that do have variants, in scale order.
VARIANT_SWARAS = ("R", "G", "M", "D", "N")


class MelakartaError(ValueError):
    """Raised when a melakarta number is outside 1..72."""


def validate_mela(mela: int) -> int:
    """Return ``mela`` if it is a legal melakarta number, else raise."""
    if not isinstance(mela, (int,)) or isinstance(mela, bool):
        raise MelakartaError(f"melakarta number must be an int, got {mela!r}")
    if not 1 <= mela <= 72:
        raise MelakartaError(f"melakarta number out of range 1..72: {mela}")
    return mela


def mela_name(mela: int) -> str:
    """Canonical melakarta name for ``mela``."""
    return MELAKARTA_NAMES[validate_mela(mela)]


def canonical_mela_name(name: str) -> str:
    """Resolve a melakarta name or common short form to its canonical name.

    Returns the input stripped when the name is not recognised, so that the
    caller can flag it rather than lose it.
    """
    stripped = (name or "").strip()
    return MELAKARTA_ALIASES.get(stripped.lower(), stripped)


def swaras_for_mela(mela: int) -> Dict[str, str]:
    """Map each variant swara letter to its variant under melakarta ``mela``.

    >>> swaras_for_mela(65)["G"], swaras_for_mela(65)["M"]
    ('G3', 'M2')
    >>> swaras_for_mela(8)["R"], swaras_for_mela(8)["N"]
    ('R1', 'N2')
    """
    validate_mela(mela)
    chakra = (mela - 1) // 6          # 0-11
    position = (mela - 1) % 6         # 0-5
    rishabha, gandhara = _PURVANGA[chakra % 6]
    dhaivata, nishada = _UTTARANGA[position]
    madhyama = "M1" if mela <= 36 else "M2"
    return {"R": rishabha, "G": gandhara, "M": madhyama,
            "D": dhaivata, "N": nishada}


def full_scale_for_mela(mela: int) -> list[str]:
    """The seven ascending swaras of melakarta ``mela``."""
    v = swaras_for_mela(mela)
    return ["S", v["R"], v["G"], v["M"], "P", v["D"], v["N"]]


def semitone(variant: str) -> int:
    """Semitone offset above the tonic for a resolved swara variant."""
    return SWARA_SEMITONES[variant]
