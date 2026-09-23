"""Raga grammar and tala templates - the hard constraints (PRD section 7).

These are *specified*, not learned.  With one composition per raga there is no
way to learn a raga's legal note set from data, but arohanam and avarohanam
state it exactly, so conformance becomes a decode-time guarantee rather than a
modelling problem.

Two ideas carry the whole design:

``RagaGrammar``
    Which swaras are legal, and which transitions are legal *given the
    direction of motion* - a raga's ascending and descending paths differ, and
    that asymmetry is most of what makes it recognisable.

``TalaTemplate``
    How many metric positions a continuation must fill, and where the strong
    beats fall.

Both expose a ``legal_next`` / mask interface that
:mod:`swaraga.decode` applies to any model's scores.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from . import config
from .melakarta import swaras_for_mela

RAGA_GRAMMAR_CONFIG = config.CONFIG_DIR / "raga_grammar.json"

#: Direction of melodic motion.
ASCENDING = "aroha"
DESCENDING = "avaroha"
EITHER = "either"


class GrammarError(ValueError):
    """Raised when a raga cannot be given a usable grammar."""


@dataclass
class RagaGrammar:
    """The legal note-space of one raga, in one composition's melakarta.

    Swaras are stored as resolved variants (``G3``, ``M1``) without octave
    marks; octave is handled separately by the decoder, since every swara is
    legal in every register the raga spans.
    """

    raga: str
    mela: int
    arohanam: List[str]                     # resolved, ascending
    avarohanam: List[str]                   # resolved, descending
    nyasa: Set[str] = field(default_factory=set)
    jeeva: Set[str] = field(default_factory=set)
    graha: Set[str] = field(default_factory=set)
    vakra: List[Tuple[str, ...]] = field(default_factory=list)
    prayogas: List[Tuple[str, ...]] = field(default_factory=list)

    # -- basic sets ---------------------------------------------------------

    @property
    def swaras(self) -> Set[str]:
        """Every swara legal anywhere in the raga."""
        return set(self.arohanam) | set(self.avarohanam)

    @property
    def scale(self) -> List[str]:
        """The raga's swaras in ascending pitch order, used for degree mapping."""
        from .melakarta import semitone

        return sorted(self.swaras, key=semitone)

    def is_legal(self, swara: str) -> bool:
        """Is this swara in the raga at all?"""
        return _base(swara) in self.swaras

    # -- transitions --------------------------------------------------------

    def legal_next(self, current: Optional[str],
                   direction: str = EITHER) -> Set[str]:
        """Swaras that may legally follow ``current``.

        ``direction`` selects the ascending or descending path; ``EITHER``
        unions both, which is the right default when the model has not
        committed to a direction.

        A ``None`` current means the phrase is starting, so the graha swaras
        apply.
        """
        if current is None:
            return set(self.graha) or set(self.swaras)

        base = _base(current)
        if base not in self.swaras:
            # Out-of-raga input: fall back to the full legal set rather than
            # returning nothing, so a bad context cannot deadlock the decoder.
            return set(self.swaras)

        allowed: Set[str] = set()
        if direction in (ASCENDING, EITHER):
            allowed |= self._neighbours(self.arohanam, base)
        if direction in (DESCENDING, EITHER):
            allowed |= self._neighbours(self.avarohanam, base)

        # Vakra phrases legalise steps that strict scale order forbids.
        for phrase in self.vakra:
            for a, b in zip(phrase, phrase[1:]):
                if a == base:
                    allowed.add(b)

        # A swara may always repeat.
        #
        # Nyasa swaras are deliberately NOT unioned in here. A resting note is
        # a legitimate place to *end*, not a note reachable from anywhere - and
        # since most of these ragas list nearly every swara as nyasa, adding
        # them would make every transition legal and erase the ascending /
        # descending asymmetry that defines the raga.
        allowed.add(base)
        return allowed & self.swaras

    @staticmethod
    def _neighbours(path: Sequence[str], base: str) -> Set[str]:
        """Swaras reachable from ``base`` along one scale path.

        Reachable means any note further along the path - Carnatic phrases skip
        notes freely (``S G P``), so restricting to strictly adjacent degrees
        would forbid ordinary music.

        The path is treated as **cyclic**: the note after the last one is the
        first, an octave away. Without that, an ascent would dead-end on the
        top swara and could never reach tara Sa, even though every arohanam
        ends by doing exactly that.
        """
        allowed: Set[str] = set()
        for index, swara in enumerate(path):
            if swara == base:
                allowed |= set(path[index + 1:])
                if index == len(path) - 1 and path:
                    allowed.add(path[0])
        return allowed

    def is_legal_transition(self, previous: str, following: str,
                            direction: str = EITHER) -> bool:
        return _base(following) in self.legal_next(previous, direction)

    # -- scale degrees (PRD section 4) --------------------------------------

    def to_degree(self, swara: str) -> Optional[int]:
        """Index of ``swara`` within this raga's own scale, or None if foreign."""
        base = _base(swara)
        scale = self.scale
        return scale.index(base) if base in scale else None

    def from_degree(self, degree: int) -> str:
        """The swara at scale index ``degree``, wrapping across octaves.

        Wrapping is what lets a degree model trained on 7-note ragas emit into
        a 5-note raga: degree 5 in a pentatonic raga means the octave above
        degree 0.
        """
        scale = self.scale
        return scale[degree % len(scale)]

    def degree_octave(self, degree: int) -> int:
        """How many octaves above the base ``degree`` lands."""
        return degree // len(self.scale)

    @property
    def n_degrees(self) -> int:
        return len(self.scale)

    # -- construction -------------------------------------------------------

    @classmethod
    def from_scales(cls, raga: str, mela: int,
                    arohanam: Sequence[str], avarohanam: Sequence[str],
                    **extra: object) -> "RagaGrammar":
        """Build a grammar from already-resolved scale strings.

        This is the path used for ragas with no entry in
        ``config/raga_grammar.json``: the dataset's own arohanam / avarohanam
        still give a correct, if less detailed, grammar.
        """
        aro = [_base(s) for s in arohanam]
        avaro = [_base(s) for s in avarohanam]
        if not aro or not avaro:
            raise GrammarError(f"{raga}: arohanam and avarohanam are both required")

        return cls(
            raga=raga,
            mela=mela,
            arohanam=aro,
            avarohanam=avaro,
            nyasa=set(extra.get("nyasa") or {aro[0]}),      # type: ignore[arg-type]
            jeeva=set(extra.get("jeeva") or set()),         # type: ignore[arg-type]
            graha=set(extra.get("graha") or {aro[0]}),      # type: ignore[arg-type]
            vakra=[tuple(v) for v in (extra.get("vakra") or [])],       # type: ignore
            prayogas=[tuple(p) for p in (extra.get("prayogas") or [])],  # type: ignore
        )


def _base(swara: str) -> str:
    """Strip octave marks, leaving the bare variant (``G3'`` -> ``G3``)."""
    return swara.rstrip("'.") if isinstance(swara, str) else swara


class RagaGrammarLibrary:
    """Loads raga grammars, preferring the curated config over bare scales."""

    def __init__(self, path: Path = RAGA_GRAMMAR_CONFIG) -> None:
        self.path = Path(path)
        if self.path.exists():
            with self.path.open(encoding="utf-8") as handle:
                self._curated = json.load(handle).get("ragas", {})
        else:
            self._curated = {}
        self._cache: Dict[Tuple[str, int], RagaGrammar] = {}

    @property
    def curated_ragas(self) -> List[str]:
        return sorted(self._curated)

    def get(self, raga: str, mela: int,
            arohanam: Optional[Sequence[str]] = None,
            avarohanam: Optional[Sequence[str]] = None) -> RagaGrammar:
        """Grammar for ``raga`` under melakarta ``mela``.

        Curated entries win.  Their scales are stored as base letters and are
        resolved to variants here, so one curated entry serves every melakarta
        the raga is notated under.
        """
        key = (raga, mela)
        if key in self._cache:
            return self._cache[key]

        entry = self._curated.get(raga)
        if entry is not None:
            variants = swaras_for_mela(mela)

            def resolve(letters: Sequence[str]) -> List[str]:
                return [letter if letter in ("S", "P") else variants[letter]
                        for letter in letters]

            grammar = RagaGrammar(
                raga=raga,
                mela=mela,
                arohanam=resolve(entry["arohanam"]),
                avarohanam=resolve(entry["avarohanam"]),
                nyasa=set(resolve(entry.get("nyasa", []))),
                jeeva=set(resolve(entry.get("jeeva", []))),
                graha=set(resolve(entry.get("graha", []))),
                vakra=[tuple(resolve(v)) for v in entry.get("vakra", [])],
                prayogas=[tuple(resolve(p)) for p in entry.get("prayogas", [])],
            )
        else:
            if arohanam is None or avarohanam is None:
                raise GrammarError(
                    f"{raga} is not in {self.path.name} and no scales were supplied"
                )
            grammar = RagaGrammar.from_scales(raga, mela, arohanam, avarohanam)

        self._cache[key] = grammar
        return grammar

    def for_row(self, row) -> RagaGrammar:
        """Grammar for one row of ``normalized_dataset.parquet``."""
        return self.get(
            row["raga"], int(row["mela"]),
            arohanam=list(row["arohanam"]), avarohanam=list(row["avarohanam"]),
        )


@dataclass(frozen=True)
class TalaTemplate:
    """The metric frame a continuation has to fill.

    ``kala`` is the number of notated positions per akshara, so one avartana
    occupies ``aksharas * kala`` positions.
    """

    tala: str
    aksharas: int
    kala: int = 2
    structure: Optional[str] = None
    metered: bool = True

    #: Notated positions per akshara, keyed by the dataset's speed labels.
    KALA_BY_SPEED = {
        "Prathama (1st speed)": 1,
        "Madhyama (2nd speed)": 2,
        "Drutam (fast)": 2,
        "Vilamba (slow)": 1,
    }

    @property
    def positions_per_avartana(self) -> int:
        return self.aksharas * self.kala

    def positions_for(self, avartanas: float) -> int:
        """How many notated positions ``avartanas`` cycles occupy."""
        return int(round(self.positions_per_avartana * avartanas))

    def is_strong_beat(self, position: int) -> bool:
        """Does ``position`` fall on an akshara boundary?

        Used to bias long notes, rests and nyasa swaras towards strong beats.
        Without a tala there are no beats, so nothing is strong.
        """
        if not self.metered or self.kala <= 0:
            return False
        return position % self.kala == 0

    def is_avartana_start(self, position: int) -> bool:
        if not self.metered or self.positions_per_avartana <= 0:
            return False
        return position % self.positions_per_avartana == 0

    @classmethod
    def from_row(cls, row) -> "TalaTemplate":
        """Template for one row of ``normalized_dataset.parquet``."""
        aksharas = int(row["tala_aksharas"] or 0)
        return cls(
            tala=row["tala"],
            aksharas=aksharas,
            kala=cls.KALA_BY_SPEED.get(row.get("speed"), 2),
            structure=row.get("tala_structure"),
            metered=bool(row.get("is_metered", True)) and aksharas > 0,
        )
