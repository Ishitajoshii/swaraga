"""Continue typed swaras with the original multi-raga B1 text model."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd

from swaraga.decode import ConstrainedDecoder
from swaraga.grammar import RagaGrammarLibrary
from swaraga.models.baseline_ngram import VariableOrderMarkov
from swaraga.windows import FOREIGN_DEGREE, build_windows, to_degrees


def parse_swaras(text, grammar):
    """Resolve bare letters against the selected raga, rejecting bad input."""
    tokens = []
    for raw in text.upper().replace("\u2019", "'").split():
        if raw in {"[REST]", "-"}:
            tokens.append("[REST]")
            continue
        match = re.fullmatch(r"([SRGMPDN])([123]?)(['.]{0,1})", raw)
        if not match:
            raise ValueError(f"Invalid swara {raw!r}. Separate notes with spaces; use S' or S. for octaves.")
        letter, variant, octave = match.groups()
        candidates = [s for s in grammar.scale if s.startswith(letter)]
        if variant:
            candidates = [s for s in candidates if s == letter + variant]
        if len(candidates) != 1:
            raise ValueError(f"{raw} is absent or ambiguous in {grammar.raga}. Scale: {' '.join(grammar.scale)}")
        tokens.append(candidates[0] + octave)
    if not tokens or all(t == "[REST]" for t in tokens):
        raise ValueError("Enter at least one swara note.")
    return tokens


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raga", default="Mohanam")
    parser.add_argument("--input", help="One phrase; omit for the interactive prompt")
    parser.add_argument("--notes", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--list-ragas", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.notes <= 128:
        parser.error("--notes must be between 1 and 128")

    frame = pd.read_parquet(ROOT / "data/processed/normalized_dataset.parquet")
    library = RagaGrammarLibrary()
    grammars = {row['raga'].casefold(): library.for_row(row) for _, row in frame.iterrows()}
    if args.list_ragas:
        print("\n".join(sorted(g.raga for g in grammars.values())))
        return
    if args.raga.casefold() not in grammars:
        parser.error("Unknown raga. Use --list-ragas to see supported names.")
    training_ids = {json.loads(line)["id"] for line in
                    (ROOT / "data/splits/train.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
    training_frame = frame[frame["id"].isin(training_ids)]
    windows = [w for w in build_windows(training_frame, rung="T2", library=library)
               if FOREIGN_DEGREE not in w.context_degrees + w.target_degrees]
    if not windows:
        parser.error("No valid training windows found.")
    model = VariableOrderMarkov().fit(windows)
    print(f"B1 text model ready: {len(windows)} windows from {len({w.record_id for w in windows})} training compositions.", flush=True)
    print("Small legacy corpus; outputs are pattern-based suggestions, not verified compositions.", flush=True)

    def predict(raga, phrase):
        grammar = grammars.get(raga.strip().casefold())
        if grammar is None:
            raise ValueError("Unknown raga. Type :ragas to list supported names.")
        tokens = parse_swaras(phrase, grammar)
        result = ConstrainedDecoder(grammar, allow_rests=False, rng=random.Random(args.seed)).decode(
            model, to_degrees(tokens, grammar), horizon=args.notes)
        print(f"Raga:   {grammar.raga}")
        print(f"Input:  {' '.join(tokens)}")
        print(f"Output: {' '.join(result.swaras)}", flush=True)
        if result.fell_back:
            print(f"Grammar fallback used for {result.fell_back} notes.", flush=True)

    if args.input is not None:
        try:
            predict(args.raga, args.input)
        except ValueError as exc:
            parser.error(str(exc))
        return

    print(f"Type swaras (default raga: {args.raga}) or Raga | swaras.")
    print("Example: Hindolam | S G M D N D M G")
    print("Commands: :ragas, :quit. Upper octave: S'; lower octave: S.", flush=True)
    while True:
        try:
            line = input("swaras> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStopped.")
            return
        if line.lower() in {":quit", "quit", "exit"}:
            return
        if line.lower() == ":ragas":
            print(", ".join(sorted(g.raga for g in grammars.values())), flush=True)
            continue
        if not line:
            continue
        raga, phrase = line.split("|", 1) if "|" in line else (args.raga, line)
        try:
            predict(raga, phrase)
        except ValueError as exc:
            print(f"Input error: {exc}", flush=True)


if __name__ == "__main__":
    main()
