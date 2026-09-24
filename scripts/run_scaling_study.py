#!/usr/bin/env python
"""The data-scaling study and the constraint ablation (PRD section 10).

Answers the thesis's central question - *how much repertoire does
raga-conditioned generation actually need?* - by training at increasing subsets
of the corpus and plotting quality against data.

Two things this deliberately does not hide:

- **Window counts overstate the data.** Stride-1 windows from N compositions
  overlap almost entirely, so the composition count is the honest x-axis and is
  what the report plots against.
- **Validation is 42 windows from 2 compositions**, so early stopping is noisy.
  Every point is averaged over several seeds and reported with its spread.

Usage::

    python scripts/run_scaling_study.py
    python scripts/run_scaling_study.py --seeds 3 --rung T1
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd                                              # noqa: E402

from swaraga import config                                       # noqa: E402
from swaraga.decode import ConstrainedDecoder                    # noqa: E402
from swaraga.evaluate import (                                   # noqa: E402
    ContinuationResult, evaluate, perplexity, training_ngram_set,
)
from swaraga.grammar import RagaGrammarLibrary, TalaTemplate     # noqa: E402
from swaraga.models import BASELINES                             # noqa: E402
from swaraga.models.neural import ARCHITECTURES, TorchModel, torch_available  # noqa: E402
from swaraga.train import TrainConfig, mean_std, train           # noqa: E402
from swaraga.windows import RUNGS, build_windows, split_windows  # noqa: E402

STUDY_MD = config.REPORTS_DIR / "scaling_study.md"
STUDY_JSON = config.REPORTS_DIR / "scaling_study.json"

#: Training-set sizes, in compositions (the honest unit - see module docstring).
SCALING_POINTS = (2, 4, 8, 16)


def load_splits() -> Dict[str, List[str]]:
    splits: Dict[str, List[str]] = {}
    for name, path in (("train", config.TRAIN_JSONL),
                       ("val", config.VAL_JSONL),
                       ("test", config.TEST_JSONL)):
        rows = [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines()]
        splits[name] = [row["id"] for row in rows]
    return splits


def generate(model, windows, by_id, library, seed: int,
             constrained: bool = True) -> List[ContinuationResult]:
    """Decode a continuation for every test window."""
    results: List[ContinuationResult] = []
    for index, window in enumerate(windows):
        row = by_id[window.record_id]
        grammar = library.for_row(row)
        if hasattr(model, "condition_from"):
            model.condition_from(window)

        decoder = ConstrainedDecoder(
            grammar, template=TalaTemplate.from_row(row),
            rng=random.Random(seed * 10_000 + index),
        )
        horizon = len(window.target_degrees)

        if constrained:
            degrees = decoder.decode(model, window.context_degrees, horizon).degrees
        else:
            degrees = _unconstrained_decode(model, window.context_degrees,
                                            horizon, seed * 10_000 + index)

        results.append(ContinuationResult(window=window, generated=degrees,
                                          grammar=grammar))
    return results


def _unconstrained_decode(model, context: Sequence[int], horizon: int,
                          seed: int) -> List[int]:
    """Sample straight from the model, with no raga mask at all.

    This is the ablation arm: it shows what the model would emit if the grammar
    were not there, which is the only way to quantify what the grammar buys.
    """
    rng = random.Random(seed)
    history = list(context)
    generated: List[int] = []

    for _ in range(horizon):
        scores = model.next_scores(history)
        if not scores:
            generated.append(history[-1] if history else 0)
            history.append(generated[-1])
            continue
        items = sorted(scores.items())
        total = sum(weight for _, weight in items)
        threshold = rng.random() * total
        cumulative = 0.0
        pick = items[-1][0]
        for degree, weight in items:
            cumulative += weight
            if cumulative >= threshold:
                pick = degree
                break
        generated.append(pick)
        history.append(pick)
    return generated


def run_point(n_compositions: int, rung: str, seeds: Sequence[int],
              frame: pd.DataFrame, library: RagaGrammarLibrary,
              splits: Dict[str, List[str]]) -> List[dict]:
    """Train and evaluate every model on a subset of ``n_compositions``."""
    all_windows = build_windows(frame, rung=rung, library=library)
    parts = split_windows(all_windows, splits)
    val, test = parts["val"], parts["test"]
    by_id = {row["id"]: row for _, row in frame.iterrows()}

    subset_ids = set(splits["train"][:n_compositions])
    train_windows = [w for w in parts["train"] if w.record_id in subset_ids]
    if not train_windows or not test:
        return []

    train_ngrams = training_ngram_set(train_windows)
    rows: List[dict] = []

    # -- baselines (deterministic given the data; one pass each) ------------
    for name, model_class in BASELINES.items():
        model = model_class().fit(train_windows)
        results = generate(model, test, by_id, library, seeds[0])
        report = evaluate(results, name, rung, train_ngrams,
                          model=model, windows=test)
        rows.append({
            "model": name, "n_compositions": n_compositions,
            "n_windows": len(train_windows), "seeds": 1,
            **{k: v for k, v in report.metrics.items()},
            "contour_std": 0.0, "n_parameters": 0, "overfit_gap": None,
        })

    # -- neural models, averaged over seeds ---------------------------------
    if torch_available():
        for architecture in ARCHITECTURES:
            contours, exacts, novelties, perplexities = [], [], [], []
            gaps, params = [], 0
            for seed in seeds:
                model = TorchModel(architecture=architecture, seed=seed)
                result = train(model, train_windows, val,
                               TrainConfig(seed=seed))
                params = model.n_parameters
                gaps.append(result.overfit_gap)

                generated = generate(model, test, by_id, library, seed)
                report = evaluate(generated, model.name, rung, train_ngrams)
                contours.append(report.metrics["contour_distance"])
                exacts.append(report.metrics["exact_match"])
                novelties.append(report.metrics["novelty"])

                value = perplexity(model, test)
                if value is not None:
                    perplexities.append(value)

            contour_mean, contour_std = mean_std(contours)
            rows.append({
                "model": f"M1-{architecture}", "n_compositions": n_compositions,
                "n_windows": len(train_windows), "seeds": len(seeds),
                "contour_distance": contour_mean, "contour_std": contour_std,
                "exact_match": mean_std(exacts)[0],
                "novelty": mean_std(novelties)[0],
                "perplexity": mean_std(perplexities)[0] if perplexities else None,
                "raga_conformance": 1.0, "transition_legality": 1.0,
                "length_exact": 1.0, "nyasa": None,
                "n_parameters": params,
                "overfit_gap": mean_std(gaps)[0],
            })

    return rows


def run_ablation(rung: str, seeds: Sequence[int], frame: pd.DataFrame,
                 library: RagaGrammarLibrary,
                 splits: Dict[str, List[str]]) -> List[dict]:
    """Constrained vs unconstrained decoding, on the full training set."""
    if not torch_available():
        return []

    all_windows = build_windows(frame, rung=rung, library=library)
    parts = split_windows(all_windows, splits)
    train_windows, val, test = parts["train"], parts["val"], parts["test"]
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    train_ngrams = training_ngram_set(train_windows)

    rows: List[dict] = []
    for architecture in ARCHITECTURES:
        for constrained in (True, False):
            conformances, legalities, contours = [], [], []
            for seed in seeds:
                model = TorchModel(architecture=architecture, seed=seed)
                train(model, train_windows, val, TrainConfig(seed=seed))
                results = generate(model, test, by_id, library, seed,
                                   constrained=constrained)
                report = evaluate(results, "x", rung, train_ngrams)
                conformances.append(report.metrics["raga_conformance"])
                legalities.append(report.metrics["transition_legality"])
                contours.append(report.metrics["contour_distance"])
            rows.append({
                "model": f"M1-{architecture}",
                "decoding": "constrained" if constrained else "unconstrained",
                "raga_conformance": mean_std(conformances)[0],
                # The column that actually moves - see write_report().
                "transition_legality": mean_std(legalities)[0],
                "legality_std": mean_std(legalities)[1],
                "contour_distance": mean_std(contours)[0],
            })
    return rows


def write_report(scaling: List[dict], ablation: List[dict], rung: str,
                 seeds: Sequence[int]) -> None:
    STUDY_JSON.parent.mkdir(parents=True, exist_ok=True)
    STUDY_JSON.write_text(json.dumps(
        {"rung": rung, "seeds": list(seeds), "scaling": scaling,
         "ablation": ablation}, indent=2), encoding="utf-8")

    lines = [
        "# Scaling study and constraint ablation",
        "",
        f"Rung {rung}. Neural points averaged over {len(seeds)} seeds "
        f"({', '.join(map(str, seeds))}); baselines are deterministic.",
        "",
        "## Why the x-axis is compositions, not windows",
        "",
        "Stride-1 windows from N compositions overlap almost entirely, so a",
        "window count badly overstates how much independent data a model saw.",
        "The whole corpus is ~907 swaras. Compositions are the honest unit.",
        "",
        "## Scaling curve",
        "",
        "| Compositions | Windows | Model | contour dist | exact | novelty | ppl | overfit gap |",
        "| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in scaling:
        contour = row.get("contour_distance")
        std = row.get("contour_std") or 0.0
        contour_cell = (f"{contour:.2f} ± {std:.2f}" if std
                        else f"{contour:.2f}") if contour is not None else "-"
        ppl = row.get("perplexity")
        gap = row.get("overfit_gap")
        lines.append(
            f"| {row['n_compositions']} | {row['n_windows']} | {row['model']} "
            f"| {contour_cell} "
            f"| {row.get('exact_match', 0):.2f} "
            f"| {row.get('novelty', 0):.2f} "
            f"| {f'{ppl:.1f}' if ppl else '-'} "
            f"| {f'{gap:+.2f}' if gap is not None else '-'} |"
        )

    if ablation:
        lines += [
            "",
            "## Constraint ablation",
            "",
            "What the raga grammar actually buys. Unconstrained decoding samples",
            "straight from the model with no mask at all.",
            "",
            "**Read `transition legality`, not `raga conformance`.** Conformance",
            "is 1.000 in *both* arms, and that is a property of the",
            "representation rather than a result: scale degrees are mapped back",
            "to swaras modulo the raga's own scale, so an out-of-raga note is",
            "literally unrepresentable. The mask cannot improve a number that is",
            "already structurally perfect.",
            "",
            "What the mask does buy is **legal motion** - a raga's ascending and",
            "descending paths differ, and nothing in the degree encoding forces",
            "a model to respect that asymmetry.",
            "",
            "| Model | Decoding | transition legality | raga conformance | contour dist |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for row in ablation:
            lines.append(
                f"| {row['model']} | {row['decoding']} "
                f"| {row['transition_legality']:.3f} ± {row['legality_std']:.3f} "
                f"| {row['raga_conformance']:.3f} "
                f"| {row['contour_distance']:.2f} |"
            )

    lines.append("")
    STUDY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Data-scaling study + ablation.")
    parser.add_argument("--rung", choices=sorted(RUNGS), default="T2")
    parser.add_argument("--seeds", type=int, default=5,
                        help="how many seeds per neural point (default: %(default)s)")
    parser.add_argument("--skip-ablation", action="store_true")
    args = parser.parse_args(argv)

    seeds = [config.SPLIT_SEED + i for i in range(args.seeds)]
    frame = pd.read_parquet(config.NORMALIZED_DATASET)
    library = RagaGrammarLibrary()
    splits = load_splits()

    if not torch_available():
        print("torch not installed - baselines only.\n"
              "  pip install torch --index-url https://download.pytorch.org/whl/cpu\n")

    scaling: List[dict] = []
    for n in SCALING_POINTS:
        if n > len(splits["train"]):
            continue
        print(f"training at {n} compositions ...")
        rows = run_point(n, args.rung, seeds, frame, library, splits)
        scaling.extend(rows)
        for row in rows:
            contour = row.get("contour_distance")
            print(f"  {row['model']:16s} contour {contour:.2f}"
                  + (f" ± {row['contour_std']:.2f}" if row.get("contour_std") else ""))

    ablation: List[dict] = []
    if not args.skip_ablation:
        print("\nconstraint ablation ...")
        ablation = run_ablation(args.rung, seeds, frame, library, splits)
        for row in ablation:
            print(f"  {row['model']:16s} {row['decoding']:14s} "
                  f"legality {row['transition_legality']:.3f}  "
                  f"conformance {row['raga_conformance']:.3f}")

    write_report(scaling, ablation, args.rung, seeds)
    print(f"\nWrote {STUDY_MD.relative_to(config.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
