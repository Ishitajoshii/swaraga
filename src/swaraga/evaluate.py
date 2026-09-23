"""Metric suite for melodic continuation (PRD section 9).

The metrics split into two kinds, and conflating them is the easiest way to
report a misleading result:

**Contract checks** - raga conformance, transition legality, exact length.
The constrained decoder guarantees these, so they should read 100% for every
model including the random walk.  They verify the system, they do not rank
models.

**Actual results** - perplexity, contour distance, nyasa appropriateness and
novelty.  These are what data buys.

Novelty is reported with every model on purpose: with ~558 windows a model that
memorises the corpus scores perfectly on everything else and is worthless.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .grammar import RagaGrammar
from .windows import Window, is_note


@dataclass
class ContinuationResult:
    """One generated continuation paired with its ground truth."""

    window: Window
    generated: List[int]
    grammar: RagaGrammar


# --- contract checks --------------------------------------------------------

def raga_conformance(result: ContinuationResult) -> float:
    """Fraction of generated notes that are in the raga."""
    real = [d for d in result.generated if is_note(d)]
    if not real:
        return 1.0
    legal = result.grammar.swaras
    in_raga = sum(1 for d in real if result.grammar.from_degree(d) in legal)
    return in_raga / len(real)


def transition_legality(result: ContinuationResult) -> float:
    """Fraction of generated transitions the grammar permits."""
    sequence = [d for d in
                list(result.window.context_degrees) + list(result.generated)
                if is_note(d)]
    if len(sequence) < 2:
        return 1.0

    legal = 0
    total = 0
    for previous, following in zip(sequence, sequence[1:]):
        total += 1
        allowed = result.grammar.legal_next(
            result.grammar.from_degree(previous)
        )
        if result.grammar.from_degree(following) in allowed:
            legal += 1
    return legal / total if total else 1.0


def length_exact(result: ContinuationResult) -> bool:
    return len(result.generated) == len(result.window.target_degrees)


# --- actual results ---------------------------------------------------------

def nyasa_appropriateness(result: ContinuationResult) -> float:
    """Does the continuation come to rest on a resting swara?"""
    real = [d for d in result.generated if is_note(d)]
    if not real:
        return 0.0
    final = result.grammar.from_degree(real[-1])
    return 1.0 if final in result.grammar.nyasa else 0.0


def contour_distance(result: ContinuationResult) -> float:
    """DTW distance between generated and true degree contours.

    Compared as intervals rather than absolute degrees: a continuation that
    makes the right *shape* one degree higher is musically much closer than the
    absolute difference suggests.
    """
    generated = _intervals(result.generated)
    truth = _intervals(result.window.target_degrees)
    if not generated or not truth:
        return 0.0 if generated == truth else 1.0
    return _dtw(generated, truth) / max(len(generated), len(truth))


#: Sakoe-Chiba band: how far the alignment may drift from the diagonal.
#:
#: Unconstrained DTW is degenerate on short symbolic sequences - it can stretch
#: one symbol to cover many, so [1,1,1,1,1,-1] and [1,-1,-1,-1,-1,-1] align at
#: zero cost despite being opposite contours. Banding forbids that while still
#: tolerating the small timing differences DTW exists to absorb.
DTW_BAND = 1


def _intervals(degrees: Sequence[int]) -> List[int]:
    real = [d for d in degrees if is_note(d)]
    return [b - a for a, b in zip(real, real[1:])]


def _dtw(a: Sequence[int], b: Sequence[int], band: int = DTW_BAND) -> float:
    """Band-constrained dynamic time warping with absolute-difference cost.

    ``band`` is the Sakoe-Chiba width; see :data:`DTW_BAND` for why an
    unconstrained version cannot be used here.
    """
    rows, cols = len(a), len(b)
    infinity = float("inf")
    # Widen the band if the sequences differ in length, or the alignment
    # could not reach the far corner at all.
    band = max(band, abs(rows - cols))

    previous = [infinity] * (cols + 1)
    previous[0] = 0.0

    for i in range(1, rows + 1):
        current = [infinity] * (cols + 1)
        low = max(1, i - band)
        high = min(cols, i + band)
        for j in range(low, high + 1):
            cost = abs(a[i - 1] - b[j - 1])
            current[j] = cost + min(previous[j], current[j - 1], previous[j - 1])
        previous = current
    return previous[cols]


def exact_match(result: ContinuationResult) -> float:
    """Fraction of positions matching the ground truth exactly."""
    truth = list(result.window.target_degrees)
    if not truth:
        return 0.0
    matches = sum(1 for g, t in zip(result.generated, truth) if g == t)
    return matches / len(truth)


def novelty(result: ContinuationResult, training_ngrams: Set[Tuple[int, ...]],
            order: int = 4) -> float:
    """1.0 means wholly novel; 0.0 means every n-gram was copied from training.

    **Never read this against 1.0.** Read it against the ground-truth reference
    row, which :func:`reference_results` produces.

    Real human continuations in this corpus score only ~0.12: the degree
    vocabulary is 15 symbols wide and the repertoire is formulaic, so heavy
    4-gram reuse is *normal music*, not memorisation. A model scoring far
    *above* the reference is not being creative - it is producing phrases
    unlike the repertoire.
    """
    grams = _ngrams(result.generated, order)
    if not grams:
        return 1.0
    copied = sum(1 for gram in grams if gram in training_ngrams)
    return 1.0 - copied / len(grams)


def _ngrams(sequence: Sequence[int], order: int) -> List[Tuple[int, ...]]:
    if len(sequence) < order:
        return []
    return [tuple(sequence[i:i + order]) for i in range(len(sequence) - order + 1)]


def training_ngram_set(windows: Iterable[Window], order: int = 4
                       ) -> Set[Tuple[int, ...]]:
    """Every degree n-gram present in the training windows."""
    grams: Set[Tuple[int, ...]] = set()
    for window in windows:
        sequence = list(window.context_degrees) + list(window.target_degrees)
        grams.update(_ngrams(sequence, order))
    return grams


def perplexity(model, windows: Iterable[Window]) -> Optional[float]:
    """Per-token perplexity, for models exposing ``probability``.

    Returns None for models that do not define a distribution (B0, B0.5, B2),
    so the report can leave the cell blank rather than invent a number.
    """
    if not hasattr(model, "probability"):
        return None

    total_log = 0.0
    total_tokens = 0
    for window in windows:
        history = list(window.context_degrees)
        for degree in window.target_degrees:
            probability = model.probability(history, degree)
            # Floor keeps a single unseen token from sending perplexity to inf,
            # which would hide every other difference between models.
            total_log += math.log(max(probability, 1e-6))
            total_tokens += 1
            history.append(degree)

    if not total_tokens:
        return None
    return math.exp(-total_log / total_tokens)


# --- aggregation ------------------------------------------------------------

@dataclass
class EvaluationReport:
    """Aggregated metrics for one model on one rung."""

    model: str
    rung: str
    n_windows: int
    metrics: Dict[str, Optional[float]] = field(default_factory=dict)

    def as_row(self) -> Dict[str, object]:
        row: Dict[str, object] = {"model": self.model, "rung": self.rung,
                                  "n": self.n_windows}
        row.update(self.metrics)
        return row


def reference_results(windows: Sequence[Window],
                      grammars: Dict[str, RagaGrammar]
                      ) -> List[ContinuationResult]:
    """The ground truth, packaged as if a model had produced it.

    Evaluating this alongside the models gives every metric a human reference
    point.  Without it, `novelty` in particular invites exactly the wrong
    conclusion (see :func:`novelty`).
    """
    return [
        ContinuationResult(
            window=window,
            generated=list(window.target_degrees),
            grammar=grammars[window.record_id],
        )
        for window in windows
    ]


def evaluate(results: Sequence[ContinuationResult], model_name: str, rung: str,
             training_ngrams: Set[Tuple[int, ...]],
             model=None, windows: Optional[Sequence[Window]] = None
             ) -> EvaluationReport:
    """Aggregate every metric over a set of generated continuations."""
    if not results:
        return EvaluationReport(model_name, rung, 0, {})

    def mean(values: Iterable[float]) -> float:
        values = list(values)
        return sum(values) / len(values) if values else 0.0

    metrics: Dict[str, Optional[float]] = {
        # contract checks
        "raga_conformance": mean(raga_conformance(r) for r in results),
        "transition_legality": mean(transition_legality(r) for r in results),
        "length_exact": mean(1.0 if length_exact(r) else 0.0 for r in results),
        # results
        "nyasa": mean(nyasa_appropriateness(r) for r in results),
        "contour_distance": mean(contour_distance(r) for r in results),
        "exact_match": mean(exact_match(r) for r in results),
        "novelty": mean(novelty(r, training_ngrams) for r in results),
    }

    if model is not None and windows is not None:
        metrics["perplexity"] = perplexity(model, windows)
    else:
        metrics["perplexity"] = None

    return EvaluationReport(model_name, rung, len(results), metrics)
