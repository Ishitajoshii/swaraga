"""Offline demo service. Symbolic generation and recorded retrieval stay separate."""
from __future__ import annotations

import json
from pathlib import Path
import random

import numpy as np
import pandas as pd

from .audio import RATE, synthesize, wav_bytes
from .decode import ConstrainedDecoder
from .grammar import RagaGrammarLibrary
from .knowledge import NotationPrior, load_knowledge
from .models.baseline_ngram import VariableOrderMarkov
from .recordings import RecordingBank, load_team_file
from .windows import FOREIGN_DEGREE, build_windows, to_degrees

PRESETS = [
    {"id": "ascent", "title": "Mohanam • ascending practice", "tokens": "S R2 G3 P D2 S' D2 P G3 R2 S R2 G3 P D2 P".split()},
    {"id": "descent", "title": "Mohanam • descending practice", "tokens": "S' D2 P G3 R2 S R2 G3 P D2 P G3 R2 S R2 G3".split()},
    {"id": "turn", "title": "Mohanam • returning to Sa", "tokens": "S G3 R2 S R2 G3 P G3 P D2 P G3 R2 G3 R2 S".split()},
]
DEFAULT_TEXT = {
    'title': 'Swaraga',
    'subtitle': 'Explore Carnatic melodies. Generate a continuation, discover vocal phrases, and hear how the music unfolds.',
    'seed_label': 'Opening phrase',
    'vocal_mode': 'Vocal library',
    'symbolic_mode': 'Generate swaras',
    'play_seed': 'Play opening phrase',
    'play_response': 'Play continuation',
    'empty_catalog': 'No vocal recordings are available in this installation. Add recordings using the recording guide in the README.',
    'vocal_explanation': 'Listen to an original phrase pair or find a compatible continuation from the library.',
    'symbolic_explanation': 'Choose an opening phrase and explore its eight-note continuation with instrumental playback.',
    'limitations': 'Vocal phrases are recorded performances. Matching selects an existing response; it does not synthesize a voice.',
}


class DemoService:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.bank = RecordingBank(self.root)
        self.copy_ready = False
        self.text = dict(DEFAULT_TEXT)
        self.warnings = list(self.bank.errors)
        try:
            module = load_team_file(root, "demo_copy")
            module._check()
            self.text.update({key: module.get_text(key) for key in DEFAULT_TEXT})
            self.copy_ready = True
        except (NotImplementedError, AssertionError):
            pass
        except (OSError, SyntaxError, AttributeError, TypeError, KeyError) as exc:
            self.warnings.append(f"Interface text unavailable; using default labels: {exc}")
        self.symbolic = {}
        self.training_count = 0
        self.composition_count = 0
        self.knowledge = {"compositions": 0, "passages": 0, "note_attacks": 0, "sources": []}
        try:
            frame = pd.read_parquet(root / "data/processed/normalized_dataset.parquet")
            training_ids = {json.loads(line)["id"] for line in (root / "data/splits/train.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()}
            training_frame = frame[frame["id"].isin(training_ids)]
            windows = [w for w in build_windows(training_frame, rung="T2") if FOREIGN_DEGREE not in w.context_degrees + w.target_degrees]
            if not windows:
                raise ValueError("No valid training windows available.")
            model = VariableOrderMarkov().fit(windows)
            try:
                compositions = load_knowledge(root)
                if compositions:
                    model = NotationPrior(model, compositions)
                    self.knowledge = {
                        "compositions": len(compositions),
                        "passages": sum(len(c["passages"]) for c in compositions),
                        "note_attacks": sum(len(p["pitch_classes"]) for c in compositions for p in c["passages"]),
                        "sources": [{"title": c["title"], "url": c["url"]} for c in compositions],
                    }
            except (ValueError, OSError, KeyError, TypeError) as exc:
                self.warnings.append(f"Notation supplement unavailable; using legacy baseline: {exc}")
            grammar = RagaGrammarLibrary().get("Mohanam", 28)
            self.training_count = len(windows)
            self.composition_count = len({w.record_id for w in windows})
            for index, preset in enumerate(PRESETS):
                decoded = ConstrainedDecoder(grammar, allow_rests=False, rng=random.Random(42 + index),
                                             max_consecutive_notes=2).decode(
                    model, to_degrees(preset["tokens"], grammar), horizon=8)
                self.symbolic[preset["id"]] = {
                    **preset, "generated": decoded.swaras, "raga": "Mohanam", "tala": "Adi (display context only)",
                    "fallback_steps": decoded.fell_back,
                    "random_seed": 42 + index,
                    "timing_note": "Opening and continuation played together with evenly spaced instrumental notes. Timing is illustrative; gamakas are not reproduced.",
                }
        except (ValueError, OSError, KeyError) as exc:
            self.warnings.append(f"Symbolic mode unavailable: {exc}")

    def state(self):
        return {"text": self.text, "symbolic": list(self.symbolic.values()),
                "recordings": self.bank.records, "warnings": self.warnings,
                "team": {"copy_ready": self.copy_ready, "catalog_ready": self.bank.friend_ready},
                "training": {"windows": self.training_count, "compositions": self.composition_count,
                             "knowledge": self.knowledge,
                             "note": "Legacy symbolic fragments have unverified provenance; overlapping windows are not independent examples. "
                             + (f"Added {self.knowledge['passages']} source-attributed notation passages from "
                                f"{self.knowledge['compositions']} Mohanam compositions as a pitch-class prior. "
                                "Source octaves and timing are not inferred. " if self.knowledge["compositions"] else "")
                             + "Practice seeds are hand-written inputs, not held-out evaluation; musical improvement is not yet measured."}}

    def response(self, query_id: str, mode: str, response_id: str | None = None):
        query = self.bank.get(query_id)
        if mode == "prepared":
            if query["split"] != "bank":
                raise ValueError("Evaluation clips are only available as retrieval queries.")
            response_id = query_id
        elif mode == "retrieval":
            ranked = self.bank.rank(query_id)
            if not ranked:
                raise ValueError("No compatible response from another source group. Try a prepared bank example.")
            response_id = response_id or ranked[0]["id"]
            if response_id not in {r["id"] for r in ranked}:
                raise ValueError("Response does not satisfy the retrieval constraints.")
        else:
            raise ValueError("Mode must be prepared or retrieval.")
        return query, self.bank.get(response_id)

    def audio(self, kind: str, key: str, part: str, mode="prepared", response_id=None):
        if part not in ("seed", "response", "combined"):
            raise ValueError("Unknown audio part.")
        if kind == "symbolic":
            if key not in self.symbolic:
                raise ValueError("Unknown symbolic example.")
            example = self.symbolic[key]
            tokens = example["tokens"] if part == "seed" else example["generated"]
            if part == "combined":
                tokens = example["tokens"] + example["generated"]
            return wav_bytes(synthesize(tokens, articulated=True))
        if kind != "vocal":
            raise ValueError("Unknown audio kind.")
        if part == "seed":
            return wav_bytes(self.bank.audio[self.bank.get(key)["id"]]["seed"])
        query, response = self.response(key, mode, response_id)
        seed = self.bank.audio[query["id"]]["seed"]
        tail = self.bank.audio[response["id"]]["response"]
        return wav_bytes(np.concatenate([seed, tail]) if part == "combined" else tail)
