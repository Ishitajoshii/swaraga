"""Parser and tokeniser for the Carnatic swara notation used in this dataset.

Source notation looks like::

    | S R G , | P D S' , | S' N D P | m G R S ||

Grammar
-------
``|``   bar line
``||``  section end
``,``   rest / note extension (karvai)
letter  a swara: ``S R G M P D N`` in either case, optionally suffixed with
        ``+`` (raised variant), ``'`` (one octave up, repeatable) or ``.``
        (one octave down, repeatable)

Case and ``+`` are recorded verbatim but are *not* trusted to determine the
variant - see :mod:`swaraga.melakarta` for why.  The parent melakarta resolves
``R G M D N`` to ``R1..R3``, ``G1..G3``, ``M1/M2``, ``D1..D3``, ``N1..N3``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple, Union

from . import config
from .melakarta import INVARIANT_SWARAS, swaras_for_mela

BAR_SYMBOL = "|"
SECTION_END_SYMBOL = "||"
REST_SYMBOL = ","

#: One swara token: letter, optional variant marker, optional octave marks.
NOTE_RE = re.compile(
    r"""^
    (?P<letter>[SsRrGgMmPpDdNn])
    (?P<marker>[+\-]?)
    (?P<octave>['.’]*)
    $""",
    re.VERBOSE,
)


class NotationError(ValueError):
    """Raised when a notation string cannot be parsed."""


@dataclass(frozen=True)
class Note:
    """A single resolved swara event."""

    swara: str            # resolved variant, e.g. "G3", "M1", "S", "P"
    letter: str           # base letter as written, upper-cased, e.g. "G"
    octave: int           # 0 = madhya, +1 = tara, -1 = mandra
    raw: str              # token exactly as it appeared in the source
    marker: str           # "+" / "-" / "" as written

    @property
    def token(self) -> str:
        """Swara with its octave written inline, e.g. G3 followed by a quote."""
        if self.octave > 0:
            return self.swara + "'" * self.octave
        if self.octave < 0:
            return self.swara + "." * (-self.octave)
        return self.swara


@dataclass(frozen=True)
class Rest:
    """A karvai / rest position."""

    raw: str = REST_SYMBOL


@dataclass(frozen=True)
class Bar:
    """A bar line within a section."""

    raw: str = BAR_SYMBOL


@dataclass(frozen=True)
class SectionEnd:
    """A section-closing double bar."""

    raw: str = SECTION_END_SYMBOL


Event = Union[Note, Rest, Bar, SectionEnd]


@dataclass
class ParsedSection:
    """One parsed section of a composition."""

    name: str
    events: List[Event] = field(default_factory=list)
    lyrics: str = ""
    raw_notation: str = ""
    unparsed_tokens: List[str] = field(default_factory=list)

    @property
    def notes(self) -> List[Note]:
        return [e for e in self.events if isinstance(e, Note)]

    @property
    def n_rests(self) -> int:
        return sum(1 for e in self.events if isinstance(e, Rest))


def _resolve_swara(letter: str, mela: int) -> str:
    """Resolve a base letter to its variant under melakarta ``mela``."""
    upper = letter.upper()
    if upper in INVARIANT_SWARAS:
        return upper
    return swaras_for_mela(mela)[upper]


def _parse_octave(marks: str) -> int:
    """An apostrophe raises an octave, a dot lowers one; returns net shift."""
    up = marks.count("'") + marks.count("’")
    down = marks.count(".")
    return up - down


def parse_notation(notation: str, mela: int) -> Tuple[List[Event], List[str]]:
    """Parse one notation string into events.

    Returns ``(events, unparsed_tokens)``.  Tokens that match no rule are
    returned rather than raising, so a single malformed token degrades one
    composition instead of failing the whole run; the caller logs them.
    """
    events: List[Event] = []
    unparsed: List[str] = []

    for raw in (notation or "").split():
        if raw == SECTION_END_SYMBOL:
            events.append(SectionEnd())
            continue
        if raw == BAR_SYMBOL:
            events.append(Bar())
            continue
        if raw == REST_SYMBOL:
            events.append(Rest())
            continue

        match = NOTE_RE.match(raw)
        if match is None:
            unparsed.append(raw)
            continue

        letter = match.group("letter")
        events.append(
            Note(
                swara=_resolve_swara(letter, mela),
                letter=letter.upper(),
                octave=_parse_octave(match.group("octave")),
                raw=raw,
                marker=match.group("marker"),
            )
        )

    return events, unparsed


def parse_sections(sections: Sequence[Dict[str, str]], mela: int) -> List[ParsedSection]:
    """Parse every section of a composition."""
    parsed: List[ParsedSection] = []
    for section in sections:
        notation = section.get("notation", "") or ""
        events, unparsed = parse_notation(notation, mela)
        parsed.append(
            ParsedSection(
                name=(section.get("name") or "").strip(),
                events=events,
                lyrics=(section.get("lyrics") or "").strip(),
                raw_notation=notation.strip(),
                unparsed_tokens=unparsed,
            )
        )
    return parsed


def to_swara_sequence(sections: Iterable[ParsedSection]) -> List[str]:
    """Flatten to the PRD section-5 sequence: swaras plus ``[REST]``.

    Octave is written inline on the swara, matching the worked example in
    ``preprocessing.md``.  Bar lines are dropped here; they are preserved in
    :func:`to_token_sequence`.
    """
    sequence: List[str] = []
    for section in sections:
        for event in section.events:
            if isinstance(event, Note):
                sequence.append(event.token)
            elif isinstance(event, Rest):
                sequence.append(config.REST)
    return sequence


def to_token_sequence(
    sections: Iterable[ParsedSection],
    tala: Optional[str] = None,
    include_sections: bool = True,
) -> List[str]:
    """Build the full model-ready token stream.

    Unlike :func:`to_swara_sequence` this keeps structure (bars, section
    boundaries, tala) and expresses register with explicit ``[OCTAVE_UP]`` /
    ``[OCTAVE_DOWN]`` markers rather than inline quotes, so every special
    token named in the PRD is exercised by exactly one representation.
    """
    tokens: List[str] = [config.BOS]
    if tala:
        tokens.append(config.TALA_TOKEN_FMT.format(tala=tala.replace(" ", "_")))

    current_octave = 0
    for section in sections:
        if include_sections and section.name:
            tokens.append(
                config.SECTION_TOKEN_FMT.format(section=section.name.replace(" ", "_"))
            )
        for event in section.events:
            if isinstance(event, Note):
                while current_octave < event.octave:
                    tokens.append(config.OCTAVE_UP)
                    current_octave += 1
                while current_octave > event.octave:
                    tokens.append(config.OCTAVE_DOWN)
                    current_octave -= 1
                tokens.append(event.swara)
            elif isinstance(event, Rest):
                tokens.append(config.REST)
            elif isinstance(event, Bar):
                tokens.append(config.BAR)
            elif isinstance(event, SectionEnd):
                tokens.append(config.SECTION_BAR)

    # Return to madhya sthayi before closing so the stream is register-balanced.
    while current_octave > 0:
        tokens.append(config.OCTAVE_DOWN)
        current_octave -= 1
    while current_octave < 0:
        tokens.append(config.OCTAVE_UP)
        current_octave += 1

    tokens.append(config.EOS)
    return tokens


def parse_scale_string(scale: str, mela: int) -> List[str]:
    """Resolve an arohanam / avarohanam string to variant swaras."""
    events, _ = parse_notation(scale, mela)
    return [e.token for e in events if isinstance(e, Note)]


def scale_letters(*scales: str) -> Set[str]:
    """Base letters used by the given arohanam / avarohanam strings."""
    letters: Set[str] = set()
    for scale in scales:
        for raw in (scale or "").split():
            match = NOTE_RE.match(raw)
            if match:
                letters.add(match.group("letter").upper())
    return letters
