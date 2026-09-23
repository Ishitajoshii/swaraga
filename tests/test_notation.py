"""Notation parsing, variant resolution and tokenisation."""

from __future__ import annotations

from swaraga import config
from swaraga.notation import (
    Bar,
    Note,
    ParsedSection,
    Rest,
    SectionEnd,
    parse_notation,
    parse_scale_string,
    parse_sections,
    scale_letters,
    to_swara_sequence,
    to_token_sequence,
)


def section(notation: str, mela: int, name: str = "Pallavi") -> ParsedSection:
    events, _ = parse_notation(notation, mela)
    return ParsedSection(name=name, events=events, raw_notation=notation)


def test_structural_symbols_are_recognised() -> None:
    events, unparsed = parse_notation("| S , | R ||", 29)
    assert unparsed == []
    assert [type(e) for e in events] == [Bar, Note, Rest, Bar, Note, SectionEnd]


def test_variants_come_from_the_mela_not_the_letter_case() -> None:
    """The same letter resolves differently under different melakartas."""
    kalyani, _ = parse_notation("G M", 65)     # G3 M2
    todi, _ = parse_notation("G M", 8)         # G2 M1
    assert [n.swara for n in kalyani] == ["G3", "M2"]
    assert [n.swara for n in todi] == ["G2", "M1"]


def test_case_does_not_change_the_resolved_variant() -> None:
    """Upper and lower case of the same letter resolve identically.

    The raw corpus writes G2 as ``G`` in one row and ``g`` in another, so case
    cannot be trusted; only the mela is.
    """
    upper, _ = parse_notation("G", 20)
    lower, _ = parse_notation("g", 20)
    assert upper[0].swara == lower[0].swara == "G2"
    # ...but the original spelling survives for traceability.
    assert (upper[0].raw, lower[0].raw) == ("G", "g")


def test_plus_marker_is_recorded_and_does_not_break_parsing() -> None:
    events, unparsed = parse_notation("G+ N+", 65)
    assert unparsed == []
    assert [n.swara for n in events] == ["G3", "N3"]
    assert [n.marker for n in events] == ["+", "+"]


def test_octave_marks() -> None:
    events, _ = parse_notation("S S' S'' S.", 29)
    assert [n.octave for n in events] == [0, 1, 2, -1]
    assert [n.token for n in events] == ["S", "S'", "S''", "S."]


def test_unparseable_tokens_are_returned_not_raised() -> None:
    events, unparsed = parse_notation("S X? R", 29)
    assert unparsed == ["X?"]
    assert [n.swara for n in events] == ["S", "R2"]


def test_swara_sequence_keeps_rests_and_inline_octaves() -> None:
    sequence = to_swara_sequence([section("| S R G , | P D S' ||", 29)])
    assert sequence == ["S", "R2", "G3", config.REST, "P", "D2", "S'"]


def test_token_sequence_structure() -> None:
    tokens = to_token_sequence([section("| S R | S' ||", 29)], tala="Misra Chapu")
    assert tokens[0] == config.BOS
    assert tokens[1] == "[TALA:Misra_Chapu]"
    assert tokens[2] == "[SECTION:Pallavi]"
    assert tokens[-1] == config.EOS
    assert config.BAR in tokens
    assert config.SECTION_BAR in tokens


def test_token_sequence_uses_explicit_octave_markers() -> None:
    tokens = to_token_sequence([section("S S' S", 29)], tala="Adi")
    assert config.OCTAVE_UP in tokens
    assert config.OCTAVE_DOWN in tokens
    # No inline quote marks in this representation.
    assert not any("'" in t for t in tokens)


def test_token_sequence_returns_to_madhya_before_eos() -> None:
    """Register markers balance out, so the stream cannot end mid-octave."""
    tokens = to_token_sequence([section("S S'", 29)], tala="Adi")
    ups = tokens.count(config.OCTAVE_UP)
    downs = tokens.count(config.OCTAVE_DOWN)
    assert ups == downs


def test_rests_survive_tokenisation() -> None:
    """The source ``tokens`` column dropped every rest; this must not."""
    notation = "| S , , | R , ||"
    assert to_swara_sequence([section(notation, 29)]).count(config.REST) == 3
    assert to_token_sequence([section(notation, 29)]).count(config.REST) == 3


def test_parse_sections_preserves_names_and_lyrics() -> None:
    parsed = parse_sections(
        [{"name": " Pallavi ", "notation": "| S R ||", "lyrics": " va ta pi "}], 29
    )
    assert parsed[0].name == "Pallavi"
    assert parsed[0].lyrics == "va ta pi"
    assert len(parsed[0].notes) == 2


def test_scale_string_resolution() -> None:
    assert parse_scale_string("S R G+ M P D N+ S'", 65) == [
        "S", "R2", "G3", "M2", "P", "D2", "N3", "S'",
    ]


def test_scale_letters_ignores_structure() -> None:
    assert scale_letters("S G m D N S'", "S' N D m G S") == {"S", "G", "M", "D", "N"}
