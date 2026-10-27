"""Hindolam generation for the pending listening review."""
import json
import random

import pandas as pd

from .decode import ConstrainedDecoder
from .grammar import RagaGrammarLibrary
from .knowledge import NotationPrior, load_knowledge
from .models.baseline_ngram import VariableOrderMarkov
from .windows import FOREIGN_DEGREE, build_windows, to_degrees

PRESETS = [
    ("Rising phrase", "S G2 M1 D1 N2 S' N2 D1 M1 G2 S G2 M1 D1 M1 G2"),
    ("Descending phrase", "S' N2 D1 M1 G2 S G2 M1 D1 N2 D1 M1 G2 S G2 M1"),
    ("Returning phrase", "M1 G2 S N2. D1. N2. S G2 M1 G2 M1 D1 N2 D1 M1 G2"),
]


def generate_examples(root):
    compositions = load_knowledge(root, "Hindolam")
    if not compositions:
        raise ValueError("Import Hindolam notation before generating review examples")
    frame = pd.read_parquet(root / "data/processed/normalized_dataset.parquet")
    train = {json.loads(line)["id"] for line in (root / "data/splits/train.jsonl").read_text(encoding="utf-8").splitlines() if line}
    windows = [w for w in build_windows(frame[frame["id"].isin(train)], rung="T2")
               if FOREIGN_DEGREE not in w.context_degrees + w.target_degrees]
    baseline = VariableOrderMarkov().fit(windows)
    model = NotationPrior(baseline, compositions, raga="Hindolam")
    grammar = RagaGrammarLibrary().get("Hindolam", 20)
    examples = []
    for index, (title, notation) in enumerate(PRESETS, 1):
        tokens = notation.split()
        result = ConstrainedDecoder(grammar, allow_rests=False, max_consecutive_notes=2,
                                    rng=random.Random(141 + index)).decode(model, to_degrees(tokens, grammar), horizon=8)
        examples.append({"id": f"symbolic-{index}", "title": title, "kind": "symbolic",
                         "seed": tokens, "response": result.swaras, "raga": "Hindolam",
                         "random_seed": 141 + index, "fallback_steps": result.fell_back,
                         "approved": False, "review_status": "pending",
                         "note": "Hand-written practice seed plus generated continuation. Uniform reference timing; no inferred tala or gamakas. Not a held-out evaluation."})
    return examples
