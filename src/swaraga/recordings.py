"""Validated catalog, manual timing annotations, and deterministic retrieval."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import re

import numpy as np

from .audio import RATE, SEMITONES, read_audio


def load_team_file(root: Path, name: str):
    spec = importlib.util.spec_from_file_location("swaraga_team_" + name, root / "team_tasks" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audio_path(root: Path, relative: str) -> Path:
    base = (root / "data/audio").resolve()
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(base) or path.suffix.lower() != ".wav":
        raise ValueError("Audio paths must be relative PCM WAV paths inside data/audio/.")
    if not path.is_file():
        raise ValueError(f"Audio file missing: {relative}")
    return path


def number(value, name: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{name} must be a finite number between {low} and {high}.")
    return float(value)


def validate_annotation(annotation: dict, durations: dict) -> None:
    if not isinstance(annotation, dict) or annotation.get("approved") is not True:
        raise ValueError("Musical review and approved=true annotation are required.")
    if not isinstance(annotation.get("group_id"), str) or not annotation["group_id"].strip():
        raise ValueError("group_id must identify the composition/seed family across all takes.")
    level = annotation.get("level", "note")
    if level == "phrase":
        if annotation.get("approved_for") != "prepared_playback":
            raise ValueError("Phrase annotations require explicit prepared-playback approval.")
        for field in ("shruti_label", "seed_notation", "response_notation", "review_scope"):
            if not isinstance(annotation.get(field), str) or not annotation[field].strip():
                raise ValueError(f"Phrase annotation needs {field}.")
        if any(key in annotation for key in ("seed_events", "response_events", "tempo_bpm", "beats_per_cycle")):
            raise ValueError("Phrase-only approval must not include unverified event or tala timing.")
        return
    if level != "note":
        raise ValueError("Annotation level must be note or phrase.")
    number(annotation.get("tonic_hz"), "tonic_hz", 60, 1000)
    bpm = number(annotation.get("tempo_bpm"), "tempo_bpm", 20, 300)
    beats = number(annotation.get("beats_per_cycle"), "beats_per_cycle", 1, 128)
    for part in ("seed", "response"):
        start = number(annotation.get(part + "_start_beat"), part + "_start_beat", 0, beats - 1e-9)
        events = annotation.get(part + "_events")
        if not isinstance(events, list) or not events:
            raise ValueError(f"{part}_events must contain manually annotated events.")
        previous_end = 0.0
        previous_pitch = None
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("Each event must be an object.")
            onset = number(event.get("onset"), "onset", 0, durations[part])
            duration = number(event.get("duration"), "duration", 0.001, durations[part])
            if abs(onset - previous_end) > 0.04 or onset + duration > durations[part] + 0.04:
                raise ValueError("Events must cover the clip in order; annotate silence as rest, without overlaps.")
            kind = event.get("kind")
            if kind not in ("note", "hold", "rest"):
                raise ValueError("Event kind must be note, hold, or rest.")
            octave = event.get("octave")
            if not isinstance(octave, int) or isinstance(octave, bool) or not -2 <= octave <= 2:
                raise ValueError("octave must be an integer from -2 to 2.")
            pitch = (event.get("swara"), octave)
            if kind == "rest":
                if event.get("swara") is not None:
                    raise ValueError("A rest must have swara=null.")
                previous_pitch = None
            else:
                if pitch[0] not in SEMITONES:
                    raise ValueError("Use an explicit swara such as G3, with octave in its own field.")
                if kind == "hold" and pitch != previous_pitch:
                    raise ValueError("A hold must extend the immediately preceding pitched event.")
                previous_pitch = pitch
            position = number(event.get("cycle_position"), "cycle_position", 0, beats - 1e-9)
            expected = (start + onset * bpm / 60) % beats
            delta = abs(position - expected)
            if min(delta, beats - delta) > 0.12:
                raise ValueError("cycle_position disagrees with onset, tempo, and clip start beat.")
            previous_end = onset + duration
        if abs(previous_end - durations[part]) > 0.04:
            raise ValueError("Events must cover the full clip, including trailing silence.")
    end_beat = (annotation["seed_start_beat"] + durations["seed"] * bpm / 60) % beats
    gap = abs(end_beat - annotation["response_start_beat"])
    if min(gap, beats - gap) > 0.15:
        raise ValueError("Seed end and paired response start must agree in tala position.")


class RecordingBank:
    def __init__(self, root: Path):
        self.root = root
        self.records = []
        self.errors = []
        self.friend_ready = False
        self.audio = {}
        try:
            module = load_team_file(root, "recording_catalog")
            records = module.RECORDINGS
            try:
                module._check()
                self.friend_ready = True
            except (AssertionError, NotImplementedError):
                pass
            annotations = json.loads((root / "data/audio/annotations.json").read_text(encoding="utf-8"))
            if not isinstance(records, list) or not isinstance(annotations, dict):
                raise ValueError("Catalog must be a list and annotations must be an object.")
            seen = set()
            groups = {}
            takes = {}
            for record in records:
                try:
                    fields = ("id", "title", "raga", "tala", "seed_path", "response_path", "source_take", "split")
                    if not isinstance(record, dict) or any(not isinstance(record.get(k), str) or not record[k].strip() for k in fields):
                        raise ValueError("Each catalog record needs all eight nonempty string fields.")
                    key = record["id"]
                    if not re.fullmatch(r"[a-zA-Z0-9_-]+", key) or key in seen:
                        raise ValueError("IDs must be unique letters/digits/underscores/hyphens.")
                    seen.add(key)
                    if record["split"] not in ("bank", "evaluation"):
                        raise ValueError("split must be bank or evaluation.")
                    annotation = annotations.get(key)
                    samples = {p: read_audio(audio_path(root, record[p + "_path"])) for p in ("seed", "response")}
                    durations = {p: len(v) / RATE for p, v in samples.items()}
                    validate_annotation(annotation, durations)
                    group = annotation["group_id"]
                    groups.setdefault(group, set()).add(record["split"])
                    takes.setdefault(record["source_take"], set()).add(record["split"])
                    self.records.append({**record, "annotation": annotation, "durations": durations})
                    self.audio[key] = samples
                except (ValueError, OSError, KeyError, TypeError) as exc:
                    self.errors.append(f"{record.get('id', 'Unnamed') if isinstance(record, dict) else 'Invalid record'}: {exc}")
            mixed = {g for g, splits in groups.items() if len(splits) > 1}
            mixed_takes = {g for g, splits in takes.items() if len(splits) > 1}
            if mixed or mixed_takes:
                raise ValueError("Bank/evaluation leakage: source groups or takes span both splits. Fix the catalog before playback.")
            self.selectable = module.list_recordings(self.records) if self.friend_ready else [r for r in self.records if r["split"] == "bank"]
        except (ValueError, OSError, SyntaxError, AttributeError, TypeError) as exc:
            self.errors.append(str(exc))
            self.records = []
            self.selectable = []
            self.audio = {}

    def get(self, clip_id: str) -> dict:
        for record in self.records:
            if record["id"] == clip_id:
                return record
        raise ValueError("Unknown or unapproved recording.")

    def rank(self, query_id: str) -> list[dict]:
        """No adaptation: match contour, tonic, tempo, meter, and join position."""
        query = self.get(query_id)
        a = query["annotation"]
        if a.get("level") == "phrase":
            return []
        ranked = []
        for candidate in self.selectable:
            b = candidate["annotation"]
            if b.get("level") == "phrase":
                continue
            if candidate["raga"] != query["raga"] or candidate["tala"] != query["tala"]:
                continue
            if a["group_id"] == b["group_id"] or query["source_take"] == candidate["source_take"]:
                continue
            if a["beats_per_cycle"] != b["beats_per_cycle"]:
                continue
            if abs(1200 * math.log2(a["tonic_hz"] / b["tonic_hz"])) > 25 or abs(a["tempo_bpm"] / b["tempo_bpm"] - 1) > 0.03:
                continue
            end = (a["seed_start_beat"] + query["durations"]["seed"] * a["tempo_bpm"] / 60) % a["beats_per_cycle"]
            gap = abs(end - b["response_start_beat"])
            if min(gap, a["beats_per_cycle"] - gap) > 0.15:
                continue
            left, right = contour(a["seed_events"]), contour(b["seed_events"])
            if left is None or right is None:
                continue
            distance = float(np.mean(np.abs(left - right)))
            duration_penalty = abs(math.log(query["durations"]["seed"] / candidate["durations"]["seed"]))
            ranked.append({"id": candidate["id"], "title": candidate["title"], "score": round(distance + duration_penalty, 5)})
        return sorted(ranked, key=lambda r: (r["score"], r["id"]))


def contour(events: list[dict]):
    pitched = [e for e in events if e["kind"] != "rest"]
    if not pitched:
        return None
    times = [e["onset"] for e in pitched]
    values = np.array([SEMITONES[e["swara"]] + 12 * e["octave"] for e in pitched])
    end = events[-1]["onset"] + events[-1]["duration"]
    # Piecewise constant annotated contour, sampled over normalized phrase time.
    positions = np.linspace(0, end, 32, endpoint=False)
    indices = np.clip(np.searchsorted(times, positions, side="right") - 1, 0, len(values) - 1)
    return values[indices] - values[0]
