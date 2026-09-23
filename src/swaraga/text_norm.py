"""Character-level repair and whitespace normalisation for metadata strings."""

from __future__ import annotations

import re
import unicodedata
from typing import List, Tuple

#: Unicode replacement character, left behind when text is decoded lossily.
REPLACEMENT_CHAR = "\ufffd"

#: The current raw dataset is clean UTF-8 and contains no replacement
#: characters, so this repair is a guard for future ingests rather than
#: something that fires today.  Where it does fire, the dash positions this
#: corpus uses (``1775<?>1835``, ``18th<?>19th``, ``Traditional <?> Tyagaraja``)
#: are all en-dash positions, so a single substitution is the right default.
#: Any occurrence is logged, so a wrong guess is visible rather than silent.
MOJIBAKE_SUBSTITUTE = "\u2013"  # EN DASH

#: Formatting characters that carry no information in this dataset.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\ufeff]")

_WHITESPACE = re.compile(r"\s+")

#: Quote / dash look-alikes folded to a single representative.
_PUNCT_FOLD = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2014": "\u2013",  # em dash -> en dash
    "\u2212": "-",       # minus sign -> hyphen
    "\u00a0": " ",       # nbsp
}


def fix_mojibake(text: str) -> Tuple[str, int]:
    """Replace lossy-decode artefacts. Returns ``(repaired, n_replaced)``."""
    if not isinstance(text, str) or REPLACEMENT_CHAR not in text:
        return text, 0
    n = text.count(REPLACEMENT_CHAR)
    return text.replace(REPLACEMENT_CHAR, MOJIBAKE_SUBSTITUTE), n


def fold_punctuation(text: str) -> str:
    """Fold quote and dash look-alikes onto a single representative each."""
    for src, dst in _PUNCT_FOLD.items():
        text = text.replace(src, dst)
    return text


def strip_control_chars(text: str) -> Tuple[str, int]:
    """Drop control and zero-width characters. Returns ``(clean, n_removed)``."""
    if not isinstance(text, str):
        return text, 0
    cleaned = _CONTROL_CHARS.sub("", text)
    return cleaned, len(text) - len(cleaned)


def collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace to a single space and strip the ends."""
    if not isinstance(text, str):
        return text
    return _WHITESPACE.sub(" ", text).strip()


def clean_text(text: str) -> Tuple[str, List[str]]:
    """Run the full metadata text cleanup.

    Returns the cleaned string plus a list of the repairs that were applied,
    so the caller can record them in the data-quality log.
    """
    if not isinstance(text, str):
        return text, []

    issues: List[str] = []
    original = text

    text = unicodedata.normalize("NFC", text)
    if text != original:
        issues.append("unicode_nfc_normalised")

    text, n_mojibake = fix_mojibake(text)
    if n_mojibake:
        issues.append(f"mojibake_repaired:{n_mojibake}")

    text, n_control = strip_control_chars(text)
    if n_control:
        issues.append(f"control_chars_removed:{n_control}")

    folded = fold_punctuation(text)
    if folded != text:
        issues.append("punctuation_folded")
        text = folded

    collapsed = collapse_whitespace(text)
    if collapsed != text:
        issues.append("whitespace_collapsed")
        text = collapsed

    return text, issues


def normalise_key(text: str) -> str:
    """Aggressive fold used for dictionary lookups only (never for output).

    Case, punctuation, diacritics and inner whitespace are all discarded so
    that ``"Muthuswamy  Dikshithar"`` and ``"muthuswami dikshithar"`` collide.
    """
    if not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return _WHITESPACE.sub(" ", text).strip()
