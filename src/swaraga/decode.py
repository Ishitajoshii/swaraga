"""Constrained decoding - where raga conformance is guaranteed (PRD section 7).

Any model that can score candidate next-degrees can be decoded here.  The
decoder masks every candidate the raga forbids *before* sampling, so a
continuation is in-raga by construction no matter how poor the model is.  That
is the whole point: it takes "is it the right raga" off the table so that
experiments measure "is it musical".

Direction matters.  A raga's ascending and descending paths differ, and that
asymmetry is most of what makes it recognisable, so the mask is chosen from the
contour of the context rather than from the note set alone.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Protocol, Sequence, Set

from . import config
from .grammar import ASCENDING, DESCENDING, EITHER, RagaGrammar, TalaTemplate
from .windows import REST_DEGREE, from_degrees, is_note

#: How far outside the madhya octave a continuation may wander, in octaves.
DEFAULT_REGISTER = (-1, 2)

#: Never emit more than this many rests in a row.
MAX_CONSECUTIVE_RESTS = 3


class NextScorer(Protocol):
    """What the decoder needs from a model.

    Returns unnormalised scores over candidate degrees.  Missing candidates are
    treated as score 0, so a model may return only the degrees it knows about.
    """

    def next_scores(self, context: Sequence[int]) -> Dict[int, float]: ...


@dataclass
class DecodeResult:
    """A generated continuation, in both encodings."""

    degrees: List[int]
    swaras: List[str]
    n_masked: int = 0               # candidates the grammar removed, summed over steps
    fell_back: int = 0              # steps where the model scored nothing legal

    def __len__(self) -> int:
        return len(self.degrees)


def infer_direction(context: Sequence[int]) -> str:
    """Ascending or descending, from the last real move in the context."""
    real = [d for d in context if is_note(d)]
    for previous, following in zip(reversed(real[:-1]), reversed(real[1:])):
        # iterating backwards over adjacent pairs
        if following > previous:
            return ASCENDING
        if following < previous:
            return DESCENDING
    return EITHER


class ConstrainedDecoder:
    """Decodes a continuation that is in-raga and of exact length."""

    def __init__(
        self,
        grammar: RagaGrammar,
        template: Optional[TalaTemplate] = None,
        register: tuple = DEFAULT_REGISTER,
        allow_rests: bool = True,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.grammar = grammar
        self.template = template
        self.register = register
        self.allow_rests = allow_rests
        self.rng = rng or random.Random(config.SPLIT_SEED)

    # -- candidate space ----------------------------------------------------

    def candidate_degrees(self) -> List[int]:
        """Every degree the decoder may ever emit, across the allowed register."""
        n = self.grammar.n_degrees
        low, high = self.register
        return list(range(low * n, high * n))

    def legal_degrees(self, context: Sequence[int]) -> Set[int]:
        """Degrees that may legally follow ``context``.

        Every degree maps to a scale swara by construction, so legality is
        entirely about *transitions* - which is exactly where a raga's
        character lives.
        """
        real = [d for d in context if is_note(d)]
        if not real:
            # Phrase start: graha swaras, in the madhya octave.
            n = self.grammar.n_degrees
            graha = {self.grammar.to_degree(s) for s in self.grammar.graha}
            allowed = {d for d in graha if d is not None}
            return allowed or set(range(n))

        current_degree = real[-1]
        current_swara = self.grammar.from_degree(current_degree)
        direction = infer_direction(context)
        legal_swaras = self.grammar.legal_next(current_swara, direction)

        allowed: Set[int] = set()
        for degree in self.candidate_degrees():
            if self.grammar.from_degree(degree) in legal_swaras:
                allowed.add(degree)

        # Keep motion local: a continuation should not leap more than an
        # octave from where the context left off.
        n = self.grammar.n_degrees
        allowed = {d for d in allowed if abs(d - current_degree) <= n}
        return allowed or set(self.candidate_degrees())

    def _rests_allowed(self, generated: Sequence[int], position: int) -> bool:
        if not self.allow_rests:
            return False
        trailing = 0
        for degree in reversed(generated):
            if degree == REST_DEGREE:
                trailing += 1
            else:
                break
        return trailing < MAX_CONSECUTIVE_RESTS

    # -- decoding -----------------------------------------------------------

    def decode(
        self,
        model: NextScorer,
        context: Sequence[int],
        horizon: int,
        temperature: float = 1.0,
        greedy: bool = False,
    ) -> DecodeResult:
        """Generate exactly ``horizon`` positions, all in-raga."""
        history = list(context)
        generated: List[int] = []
        n_masked = 0
        fell_back = 0

        for step in range(horizon):
            legal = self.legal_degrees(history)
            if self._rests_allowed(generated, step):
                legal = legal | {REST_DEGREE}

            scores = model.next_scores(history)
            n_masked += sum(1 for d in scores if d not in legal)

            masked = {d: s for d, s in scores.items() if d in legal and s > 0}
            if masked:
                choice = self._pick(masked, temperature, greedy)
            else:
                # The model knows nothing legal here; the grammar still does.
                fell_back += 1
                choice = self._pick({d: 1.0 for d in legal}, temperature, greedy)

            generated.append(choice)
            history = list(history) + [choice]

        return DecodeResult(
            degrees=generated,
            swaras=from_degrees(generated, self.grammar),
            n_masked=n_masked,
            fell_back=fell_back,
        )

    def _pick(self, scores: Dict[int, float], temperature: float,
              greedy: bool) -> int:
        if greedy:
            best = max(scores.values())
            # Deterministic tie-break, so greedy decoding is reproducible.
            return min(d for d, s in scores.items() if s == best)

        if temperature <= 0:
            return self._pick(scores, temperature, greedy=True)

        items = sorted(scores.items())
        weights = [math.pow(max(s, 1e-12), 1.0 / temperature) for _, s in items]
        total = sum(weights)
        if total <= 0:
            return self.rng.choice([d for d, _ in items])

        threshold = self.rng.random() * total
        cumulative = 0.0
        for (degree, _), weight in zip(items, weights):
            cumulative += weight
            if cumulative >= threshold:
                return degree
        return items[-1][0]


def horizon_for(rung_spec: Dict[str, object], template: TalaTemplate) -> int:
    """Continuation length in notated positions, for an avartana-based rung."""
    if rung_spec["unit"] == "notes":
        return int(rung_spec["horizon"])
    return template.positions_for(float(rung_spec["horizon"]))
