"""Build source-attributed Hindolam audio and notation for human listening review.

Offline after fetch_hindolam_sources.py and the documented FFmpeg conversion.
Never modifies the active vocal catalog or creates a listening approval.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.audio import RATE, read_audio, synthesize, wav_bytes
from swaraga.hindolam import generate_examples
from swaraga.knowledge import extract_composition

CACHE = ROOT / ".demo-artifacts/hindolam-sources"
OUT = ROOT / "data/audio/hindolam_review"
NOTATION_URL = "https://www.shivkumar.org/music/samajavaragamana.htm"
AUDIO_URL = "https://www.shivkumar.org/music/samajavaragamana.mp3"
RIGHTS_URL = "https://www.shivkumar.org/music/background.html"
GROUP = "tyagaraja_samaja_vara_gamana"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def quiet_boundary(samples, seconds, radius=2):
    """Find a low-energy 40 ms interval, then its quietest sample.

    This reduces cut noise; it does not establish a musical phrase boundary.
    """
    begin, end = round((seconds - radius) * RATE), round((seconds + radius) * RATE)
    if begin < 0 or end > len(samples):
        raise ValueError("Boundary search falls outside source recording")
    hop, width = round(.01 * RATE), round(.04 * RATE)
    starts = np.arange(begin, end - width, hop)
    energies = [np.mean(samples[i:i + width] ** 2) for i in starts]
    start = int(starts[int(np.argmin(energies))])
    return start + int(np.argmin(np.abs(samples[start:start + width])))


def pitch_analysis(samples):
    """Exploratory YIN-like F0, independent of the expected Hindolam swaras.

    70-500 Hz, 128 ms windows, 40 ms hop. Drone/voice confusion is possible;
    results are not converted into approved note/tala annotations.
    """
    taps = np.arange(-48, 49)
    kernel = np.sinc(taps / 3) * np.hamming(len(taps))
    x = np.convolve(samples, kernel / kernel.sum(), mode="same")[::3]
    rows = []
    for offset in range(0, len(x) - 1024, 320):
        frame = x[offset:offset + 1024]
        frame = frame - frame.mean()
        windows = np.lib.stride_tricks.sliding_window_view(frame, 512)
        difference = np.sum((windows[1:116] - frame[:512]) ** 2, axis=1)
        normalized = difference * np.arange(1, 116) / np.maximum(np.cumsum(difference), 1e-15)
        choices = [k for k in range(15, 113) if normalized[k] < .2
                   and normalized[k] <= normalized[k - 1] and normalized[k] < normalized[k + 1]]
        k = choices[0] if choices else int(np.argmin(normalized[15:113])) + 15
        denominator = normalized[k - 1] - 2 * normalized[k] + normalized[k + 1]
        shift = np.clip(.5 * (normalized[k - 1] - normalized[k + 1]) / denominator, -.5, .5) if denominator else 0
        rows.append([(offset + 512) / 8000, 8000 / (k + 1 + shift),
                     float(np.clip(1 - normalized[k], 0, 1)), float(np.sqrt(np.mean(frame ** 2)))])
    track = np.asarray(rows)
    good = track[(track[:, 2] >= .9) & (track[:, 3] >= .02)]
    return track, {"frames": len(track), "confident_frames": len(good),
                   "confident_fraction": round(len(good) / len(track), 4),
                   "median_f0_hz": round(float(np.median(good[:, 1])), 2) if len(good) else None,
                   "scope": "Diagnostic F0 only. No tonic, swaras, gamakas or tala inferred as ground truth."}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    old = OUT / "review.json"
    if old.exists() and any(x.get("approved") for x in json.loads(old.read_text(encoding="utf-8"))["items"]):
        raise ValueError("Review already approved; use a new version instead of overwriting")
    notation = CACHE / "samajavaragamana.html"
    source = {
        "id": GROUP, "title": "Samaja Vara Gamana", "composer": "Tyagaraja", "raga": "Hindolam",
        "tala": "Adi", "kalai": None, "version": "Peri Sriramamurthy",
        "archive": "Shivkumar Kalyanaraman Carnatic Music Krithi Archive",
        "url": NOTATION_URL, "accessed": "2026-10-27", "encoding": "cp1252", "file": notation.name,
        "sha256": digest(notation), "rights_url": RIGHTS_URL,
        "rights_note": "Archive author permits noncommercial copying and distribution with attribution; custom permission, not a Creative Commons license.",
    }
    manifest_path = ROOT / "data/knowledge/hindolam_sources.json"
    if manifest_path.exists():
        pinned = json.loads(manifest_path.read_text(encoding="utf-8"))["sources"][0]
        if source["sha256"] != pinned["sha256"]:
            raise ValueError("Notation source changed; review its new edition before rebuilding")
    composition = extract_composition(notation.read_bytes(), source)
    write_json(manifest_path, {"schema_version": 1, "sources": [source]})
    write_json(ROOT / "data/knowledge/hindolam_notation.json", {"schema_version": 1, "compositions": [composition]})
    original = CACHE / "samajavaragamana.mp3"
    working = CACHE / "samajavaragamana.f32"
    source_info = {
        "title": "Samaja Vara Gamana", "composer": "Tyagaraja", "raga": "Hindolam", "tala": "Adi",
        "performer_credit": "Shivkumar Kalyanaraman (archive rendition, following Peri Sriramamurthy's version)",
        "audio_url": AUDIO_URL, "notation_url": NOTATION_URL, "rights_url": RIGHTS_URL,
        "rights_note": source["rights_note"], "source_sha256": digest(original), "working_sha256": digest(working),
        "accessed": "2026-10-27", "group_id": GROUP, "working_format": "float32 little-endian, mono, 24000 Hz",
    }
    if old.exists() and json.loads(old.read_text(encoding="utf-8"))["source"]["source_sha256"] != source_info["source_sha256"]:
        raise ValueError("Audio source changed; review it before overwriting existing cuts")
    # Decode float first: MP3 reconstruction can exceed nominal full scale.
    # Attenuate once before integer PCM export rather than clipping on decode.
    samples = np.fromfile(working, dtype="<f4").astype(float)
    if not len(samples) or not np.isfinite(samples).all() or len(samples) > RATE * 600:
        raise ValueError("Invalid float working audio")
    source_info.update({"duration_seconds": len(samples) / RATE,
                        "peak_before": float(np.max(np.abs(samples))),
                        "above_nominal_full_scale_fraction": float(np.mean(np.abs(samples) > 1)),
                        "audio_type": "Archive vocal rendition; source accompaniment retained"})
    gain = min(1.0, .85 / max(float(np.max(np.abs(samples))), 1e-12))
    items = []
    # Deliberately separated source regions, not multiple takes/compositions.
    for index, targets in enumerate(((70, 80, 90), (185, 195, 205), (300, 310, 320)), 1):
        a, b, c = [quiet_boundary(samples, t) for t in targets]
        if not a < b < c or (c - a) / RATE > 28:
            raise ValueError("Invalid proposed cut")
        original_clip = samples[a:c]
        clip = original_clip.copy() * gain
        fade = round(.008 * RATE)
        clip[:fade] *= np.linspace(0, 1, fade)
        clip[-fade:] *= np.linspace(1, 0, fade)
        cut = b - a
        part_samples = {"seed": clip[:cut], "response": clip[cut:], "combined": clip}
        key = f"vocal-{index}"
        paths, hashes = {}, {}
        for part, values in part_samples.items():
            path = OUT / f"{key}-{part}.wav"
            path.write_bytes(wav_bytes(values))
            paths[part], hashes[part] = path.name, digest(path)
        track, diagnostic = pitch_analysis(original_clip)
        np.savez_compressed(OUT / f"{key}-pitch.npz", track=track)
        items.append({"id": key, "title": f"Vocal excerpt {index}", "kind": "vocal", "paths": paths,
                      "sha256": hashes, "approved": False, "review_status": "rejected",
                      "swara_only_verified": False,
                      "rejection_reason": "User confirmed these excerpts contain lyrics, not only swara syllables. Withdrawn from the swaram-only pipeline.",
                      "group_id": GROUP, "split": "review_only", "source_seconds": [a / RATE, b / RATE, c / RATE],
                      "durations": {part: len(values) / RATE for part, values in part_samples.items()},
                      "analysis": diagnostic, "source_peak": float(np.max(np.abs(original_clip))),
                      "source_above_nominal_full_scale_fraction": float(np.mean(np.abs(original_clip) > 1)),
                      "gain": gain, "edge_fade_seconds": .008,
                      "join_sample_jump": float(abs(clip[cut] - clip[cut - 1])),
                      "note": "Original contiguous excerpt. Low-energy cuts proposed automatically; phrase endpoints need your review. Swara transcription and tala alignment are not verified."})
    for item in generate_examples(ROOT):
        key = item["id"]
        paths, hashes = {}, {}
        for part, tokens in (("seed", item["seed"]), ("response", item["response"]), ("combined", item["seed"] + item["response"])):
            path = OUT / f"{key}-{part}.wav"
            path.write_bytes(wav_bytes(synthesize(tokens, tonic_hz=240, articulated=True)))
            paths[part], hashes[part] = path.name, digest(path)
        items.append({**item, "paths": paths, "sha256": hashes, "split": "review_only"})
    review = {"schema_version": 1, "review_id": "hindolam-v2-vocals-withdrawn", "approved": False,
              "vocal_status": "No eligible swaram-only vocal examples. V1-V3 rejected after user content review.",
              "source": source_info, "notation": {"compositions": 1, "passages": len(composition["passages"]),
              "written_notes": sum(len(p["pitch_classes"]) for p in composition["passages"])},
              "items": items, "evaluation_note": "All vocal excerpts and notation share one composition group; this is a development listening review, not held-out evaluation.",
              "saraga_status": "Govardhana Girisham metadata, tonic and sama obtained; audio unavailable (Zenodo HTTP 403 network restriction). Not used for these clips."}
    write_json(old, review)
    write_json(ROOT / "reports/hindolam_review_checks.json", {
        "source": source_info, "notation": review["notation"],
        "vocal_checks": [{k: i[k] for k in ("id", "source_seconds", "durations", "analysis", "source_peak", "source_above_nominal_full_scale_fraction", "join_sample_jump")} for i in items if i["kind"] == "vocal"],
        "status": "Vocal preparation incomplete: V1-V3 rejected for lyric content. Instrumental examples remain pending.",
        "vocal_content_verified": False,
        "saraga_status": review["saraga_status"], "evaluation_note": review["evaluation_note"],
    })
    print(json.dumps({"review": str(old), "notation": review["notation"],
                      "eligible_vocal_pairs": 0, "rejected_vocal_pairs": 3, "symbolic_pairs": 3, "approved": False}, indent=2))


if __name__ == "__main__":
    main()
