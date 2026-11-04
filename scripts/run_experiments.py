#!/usr/bin/env python
"""Run the v1 baseline suite and write the results report.

Reproduces every number quoted in `reports/baseline_results.md`.

Usage::

    python scripts/run_experiments.py
    python scripts/run_experiments.py --rung T1 --seed 7
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Dict, List

SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd                                          # noqa: E402

from swaraga import config                                   # noqa: E402
from swaraga.decode import ConstrainedDecoder                # noqa: E402
from swaraga.evaluate import (                               # noqa: E402
    ContinuationResult, EvaluationReport, evaluate, reference_results,
    training_ngram_set,
)
from swaraga.grammar import RagaGrammarLibrary, TalaTemplate  # noqa: E402
from swaraga.models import BASELINES                         # noqa: E402
from swaraga.models.neural import (                          # noqa: E402
    ARCHITECTURES, TorchModel, torch_available,
)
from swaraga.train import TrainConfig, train as train_model  # noqa: E402
from swaraga.windows import RUNGS, build_windows, split_windows  # noqa: E402

RESULTS_MD = config.REPORTS_DIR / "baseline_results.md"
RESULTS_JSON = config.REPORTS_DIR / "baseline_results.json"


def load_splits() -> Dict[str, List[str]]:
    """Composition ids per split, from the preprocessing stage."""
    splits: Dict[str, List[str]] = {}
    for name, path in (("train", config.TRAIN_JSONL),
                       ("val", config.VAL_JSONL),
                       ("test", config.TEST_JSONL)):
        rows = [json.loads(line) for line in
                path.read_text(encoding="utf-8").splitlines()]
        splits[name] = [row["id"] for row in rows]
    return splits


def run_rung(frame: pd.DataFrame, rung: str, seed: int,
             library: RagaGrammarLibrary) -> List[EvaluationReport]:
    """Train and evaluate every baseline on one rung."""
    windows = build_windows(frame, rung=rung, library=library)
    if not windows:
        return []

    parts = split_windows(windows, load_splits())
    train, test = parts["train"], parts["test"]
    if not train or not test:
        return []

    train_ngrams = training_ngram_set(train)
    by_id = {row["id"]: row for _, row in frame.iterrows()}
    grammars = {rid: library.for_row(row) for rid, row in by_id.items()}
    reports: List[EvaluationReport] = []

    # The human reference row first, so every model below is read against it
    # rather than against a theoretical ideal.
    reports.append(
        evaluate(reference_results(test, grammars), "GT", rung, train_ngrams)
    )

    for name, model_class in BASELINES.items():
        model = model_class().fit(train)
        results: List[ContinuationResult] = []

        for index, window in enumerate(test):
            row = by_id[window.record_id]
            grammar = library.for_row(row)
            decoder = ConstrainedDecoder(
                grammar,
                template=TalaTemplate.from_row(row),
                # Per-window seed: deterministic overall, but not the same
                # draw for every window.
                rng=random.Random(seed * 10_000 + index),
            )
            decoded = decoder.decode(
                model, window.context_degrees, len(window.target_degrees),
            )
            results.append(
                ContinuationResult(window=window, generated=decoded.degrees,
                                   grammar=grammar)
            )

        reports.append(
            evaluate(results, name, rung, train_ngrams,
                     model=model, windows=test)
        )

    # -- M1 neural models ---------------------------------------------------
    # Skipped silently without torch, so the baseline suite keeps running in a
    # light environment (PRD section 8.2).
    if torch_available():
        val = parts["val"]
        for architecture in ARCHITECTURES:
            model = TorchModel(architecture=architecture, seed=seed)
            train_config = TrainConfig(seed=seed)
            result = train_model(model, train, val, train_config)
            result.save_history(
                config.REPORTS_DIR / "training_history" / f"{rung}_{architecture}_seed{seed}.json",
                train_config, rung=rung, train_windows=len(train), val_windows=len(val),
            )
            results = []
            for index, window in enumerate(test):
                row = by_id[window.record_id]
                grammar = grammars[window.record_id]
                model.condition_from(window)
                decoder = ConstrainedDecoder(
                    grammar, template=TalaTemplate.from_row(row),
                    rng=random.Random(seed * 10_000 + index),
                )
                decoded = decoder.decode(
                    model, window.context_degrees, len(window.target_degrees),
                )
                results.append(
                    ContinuationResult(window=window, generated=decoded.degrees,
                                       grammar=grammar)
                )
            # perplexity() re-conditions per window itself.
            reports.append(
                evaluate(results, model.name, rung, train_ngrams,
                         model=model, windows=test)
            )

    return reports


def write_report(all_reports: Dict[str, List[EvaluationReport]],
                 window_stats: Dict[str, dict], seed: int) -> None:
    payload = {
        "seed": seed,
        "window_stats": window_stats,
        "results": {rung: [r.as_row() for r in reports]
                    for rung, reports in all_reports.items()},
    }
    RESULTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines: List[str] = [
        "# Baseline results",
        "",
        f"Seed {seed}. Reproduce with `python scripts/run_experiments.py`.",
        "",
        "Contract checks (`raga_conformance`, `transition_legality`,",
        "`length_exact`) are guaranteed by the constrained decoder and read",
        "1.00 for every model including the random walk - they verify the",
        "system, they do not rank models. The columns that rank models are",
        "`contour_distance` (lower is better), `exact_match`, `nyasa` and",
        "`perplexity`.",
        "",
        "**`GT` is the ground truth**, scored as if it were a model. Read",
        "every row against it, not against a theoretical ideal - most",
        "importantly `novelty`, where real human continuations score only",
        "~0.12 because the degree vocabulary is 15 symbols wide and the",
        "repertoire is formulaic. Heavy n-gram reuse is normal music here.",
        "",
    ]

    for rung, reports in all_reports.items():
        if not reports:
            continue
        stats = window_stats.get(rung, {})
        lines += [
            f"## {rung} - {RUNGS[rung]['label']}",
            "",
            f"{stats.get('total', 0)} windows from "
            f"{stats.get('compositions_contributing', 0)} compositions "
            f"covering {stats.get('ragas_covered', 0)} ragas.",
            "",
            "| Model | n | conform | legal | len | nyasa | contour dist | exact | novelty | ppl |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for report in reports:
            m = report.metrics
            ppl = m.get("perplexity")
            lines.append(
                f"| {report.model} | {report.n_windows} "
                f"| {m['raga_conformance']:.2f} "
                f"| {m['transition_legality']:.2f} "
                f"| {m['length_exact']:.2f} "
                f"| {m['nyasa']:.2f} "
                f"| {m['contour_distance']:.2f} "
                f"| {m['exact_match']:.2f} "
                f"| {m['novelty']:.2f} "
                f"| {f'{ppl:.1f}' if ppl else '-'} |"
            )
        lines.append("")

    RESULTS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the v1 baseline suite.")
    parser.add_argument("--rung", choices=sorted(RUNGS), default=None,
                        help="only this rung (default: all)")
    parser.add_argument("--seed", type=int, default=config.SPLIT_SEED)
    args = parser.parse_args(argv)

    frame = pd.read_parquet(config.NORMALIZED_DATASET)
    library = RagaGrammarLibrary()
    rungs = [args.rung] if args.rung else list(RUNGS)

    all_reports: Dict[str, List[EvaluationReport]] = {}
    window_stats: Dict[str, dict] = {}

    for rung in rungs:
        windows = build_windows(frame, rung=rung, library=library)
        window_stats[rung] = {
            "total": len(windows),
            "compositions_contributing": len({w.record_id for w in windows}),
            "ragas_covered": len({w.raga for w in windows}),
        }
        all_reports[rung] = run_rung(frame, rung, args.seed, library)

    write_report(all_reports, window_stats, args.seed)

    for rung, reports in all_reports.items():
        if not reports:
            print(f"{rung}: skipped (too few windows in train or test)")
            continue
        print(f"\n{rung} - {RUNGS[rung]['label']}  "
              f"({window_stats[rung]['total']} windows)")
        print(f"  {'model':16s} {'contour':>8s} {'exact':>7s} "
              f"{'nyasa':>7s} {'novelty':>8s} {'ppl':>8s}")
        for report in reports:
            m = report.metrics
            ppl = m.get("perplexity")
            print(f"  {report.model:16s} {m['contour_distance']:8.2f} "
                  f"{m['exact_match']:7.2f} {m['nyasa']:7.2f} "
                  f"{m['novelty']:8.2f} "
                  f"{f'{ppl:8.1f}' if ppl else '       -'}")

    print(f"\nWrote {RESULTS_MD.relative_to(config.PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
