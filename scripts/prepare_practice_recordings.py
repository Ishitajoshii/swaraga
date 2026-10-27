"""Prepare takes 30-32 for listening review; never approve or register them.

MP3 decoding uses the existing FFmpeg adapter. Reruns decode the originals
again so sample quantization stays consistent with the existing review cuts.
"""
import hashlib
import html
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.audio import RATE, read_audio, wav_bytes
from analyze_take29 import align, pitch_track

EXERCISES = [
    (30, "S R G P G R S R", "G P D P G R S S"),
    (31, "G P D S' D P G R", "S R G P G R S S"),
    (32, "S G R S R G P G", "P D P G R G R S"),
]


def save_audio(path, samples):
    content = wav_bytes(samples)
    if path.exists() and path.read_bytes() != content:
        raise ValueError(f"Refusing to overwrite different audio: {path}")
    if not path.exists():
        path.write_bytes(content)


def notes_for(opening, response):
    return [{"swara": token.rstrip("'"), "expected_octave": token.count("'"),
             "units": 1, "phrase": label}
            for label, sequence in (("Opening", opening), ("Continuation", response))
            for token in sequence.split()]


def process(take, opening, response):
    folder = ROOT / "data/audio"
    catalog_annotations = json.loads((folder / "annotations.json").read_text(encoding="utf-8"))
    if f"mohanam_take{take}" in catalog_annotations:
        raise ValueError(f"Take {take} is already registered; use a new take ID for revised cuts.")
    source = folder / f"Standard recording {take}.mp3"
    working = folder / f"mohanam_take{take}_review.wav"
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    samples = read_audio(source)
    save_audio(working, samples)
    track = pitch_track(samples)
    if not len(track):
        raise ValueError(f"Take {take}: too short for pitch analysis")
    good = track[(track[:, 2] > .85) & (track[:, 3] > .025)]
    nominal = 440 * 2 ** ((56 - 69) / 12)
    relative = 12 * np.log2(good[:, 1] / nominal)
    error = (relative[:, None] - np.array([0, 2, 4, 7, 9]) + 6) % 12 - 6
    nearest = error[np.arange(len(error)), np.argmin(np.abs(error), axis=1)]
    central = nearest[np.abs(nearest) < .5]
    if not len(central):
        raise ValueError(f"Take {take}: no reliable tonic estimate near supplied G#")
    tonic = nominal * 2 ** (float(np.median(central)) / 12)
    notes = notes_for(opening, response)
    spans = align(track, notes, tonic)
    start, split, end = spans[0]["start_seconds"], spans[8]["start_seconds"], spans[-1]["end_seconds"]
    paths = {}
    for part, a, b in (("seed", start, split), ("response", split, end), ("combined", start, end)):
        path = folder / f"mohanam_take{take}_{part}_draft.wav"
        save_audio(path, samples[round(a * RATE):round(b * RATE)])
        paths[part] = path.relative_to(ROOT).as_posix()
    starts = np.array([n["start_seconds"] for n in spans])
    # Descriptive timing fit only: it must not become verified tala annotation.
    seconds_per_note, offset = np.polyfit(np.arange(len(starts)), starts, 1)
    residuals = starts - (offset + seconds_per_note * np.arange(len(starts)))
    result = {
        "id": f"mohanam_take{take}", "take": take, "approved": False,
        "source": source.relative_to(ROOT).as_posix(), "source_sha256": digest,
        "working_copy": working.relative_to(ROOT).as_posix(),
        "exercise_assignment": "Assumed take order 30/31/32 matches exercises 1/2/3; checked against pitch below.",
        "notation_confirmation": "Ishita explicitly confirmed recording 32 follows the supplied exercise despite uncertain pitch estimates." if take == 32 else "Reference is the requested exercise; phrase review pending.",
        "raga": "Mohanam", "tala_requested": "Adi", "shruti_requested": "G# / 5.5",
        "opening": opening, "continuation": response,
        "duration_seconds": len(samples) / RATE,
        "decoded_peak_dbfs": float(20 * np.log10(max(float(np.max(np.abs(samples))), 1e-12))),
        "samples_at_or_above_0_999": int(np.count_nonzero(np.abs(samples) >= .999)),
        "tonic_hz_estimate": round(tonic, 3),
        "fitted_bpm_if_one_note_per_beat": round(60 / seconds_per_note, 2),
        "timing_fit_max_residual_seconds": round(float(np.max(np.abs(residuals))), 3),
        "start_seconds": start, "split_seconds": split, "end_seconds": end,
        "paths": paths, "notes": spans,
        "limitations": [
            "Notation-guided estimates, not independent transcription or listening approval.",
            "Repeated-note boundaries use a duration prior; breaths and gamakas can reduce pitch agreement.",
            "Tempo fit assumes the requested one-note-per-beat convention; tala phase is unverified.",
            "All files remain outside the approved demo bank pending phrase listening review."
        ]
    }
    result["octave_mismatches"] = [i + 1 for i, n in enumerate(spans)
                                    if n["octave_estimate"] is not None
                                    and n["octave_estimate"] != notes[i]["expected_octave"]]
    result["notes_flagged"] = sum(n["review_needed"] for n in spans)
    (folder / f"mohanam_take{take}_intake.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    artifacts = ROOT / ".demo-artifacts" / f"take{take}"
    artifacts.mkdir(parents=True, exist_ok=True)
    np.savetxt(artifacts / "pitch.csv", track, delimiter=",", header="seconds,hz,periodicity,rms", comments="")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
    return result


def review_page(results):
    cards = []
    for r in results:
        players = []
        for part, label in (("seed", "1. Opening"), ("response", "2. Continuation"), ("combined", "3. Together")):
            file = html.escape(Path(r["paths"][part]).name)
            players.append(f'<div><label>{label}</label><audio controls preload="metadata" src="{file}"></audio></div>')
        detail = ('<p>Notes confirmed by you. The pitch estimate is uncertain near the end of the opening; this is not a request to re-record.</p>' if r['take'] == 32 else '')
        cards.append(f'''<section><h2>Recording {r['take']}</h2>{detail}
<p><b>Opening:</b> <code>{html.escape(r['opening'])}</code><br>
<b>Continuation:</b> <code>{html.escape(r['continuation'])}</code></p>
<div class="players">{''.join(players)}</div>
<details><summary>Cut timestamps</summary><p>From {r['start_seconds']:.2f} s;
continuation starts at {r['split_seconds']:.2f} s; ends at {r['end_seconds']:.2f} s in the original recording.</p></details></section>''')
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Mohanam recordings 30–32</title>
<style>body{font:17px/1.6 system-ui;color:#173b39;background:#f6f4ee;max-width:1050px;margin:40px auto;padding:0 22px}
h1{font-size:32px;line-height:1.2}section{padding:24px;background:white;border:1px solid #d9dfd9;border-radius:14px;margin:22px 0}
h2{margin-top:0}.players{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}audio{width:100%;margin-top:10px}
label{font-weight:600}code{font-size:17px}summary{cursor:pointer}details{margin-top:15px;color:#53635f}
@media(max-width:750px){.players{grid-template-columns:1fr}}</style>
<h1>Your three Mohanam exercises</h1><p>Draft phrase cuts, ready for your listening check.</p>
<p>For each recording, play <b>Opening</b>, <b>Continuation</b>, then <b>Together</b>.
Check that the split falls after the eighth swara and that no swara or gamaka is cut off.
You only need to report the recording number if something sounds wrong.</p>
CARDS
<p>Your originals are unchanged. These are prepared excerpts of your own performance.
Pitch, note timing and tala alignment remain provisional.</p>
<script>const players=[...document.querySelectorAll('audio')];for(const p of players){p.addEventListener('play',()=>{for(const other of players)if(other!==p)other.pause();});}</script></html>'''.replace('CARDS', ''.join(cards))
    if all(r.get("phrase_playback_approved") for r in results):
        page = page.replace("Draft phrase cuts, ready for your listening check.",
                            "All three phrase cuts and joins approved by Ishita; available in the local demo's Prepared example mode.")
        page = page.replace("You only need to report the recording number if something sounds wrong.",
                            "Your phrase listening review is complete.")
    (ROOT / "data/audio/mohanam_practice_review.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    results = [process(*exercise) for exercise in EXERCISES]
    review_page(results)
    for r in results:
        print(json.dumps({key: r[key] for key in ("take", "duration_seconds", "decoded_peak_dbfs",
              "samples_at_or_above_0_999", "tonic_hz_estimate", "fitted_bpm_if_one_note_per_beat",
              "timing_fit_max_residual_seconds", "start_seconds", "split_seconds", "end_seconds",
              "notes_flagged", "octave_mismatches")}, indent=2))
