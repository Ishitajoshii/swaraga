"""Create review-only beat maps and click overlays for self-counted takes.

No approved audio, catalog, or annotations are changed. Candidate attacks were
selected by inspecting spectral-flux peaks independently of pitch settling.
The singer must review them before they can become musical timing annotations.
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
from swaraga.recordings import validate_annotation

# Seconds in original takes, not in the trimmed clips. These are proposed
# syllable attacks, not claims of verified tala or independently decoded swaras.
ATTACKS = {
    30: [.20, 1.15, 2.09, 2.99, 3.96, 4.85, 5.78, 6.69,
         7.75, 8.73, 9.62, 10.58, 11.57, 12.55, 13.54, 14.74],
    31: [.22, 1.23, 2.28, 3.28, 4.23, 5.08, 5.98, 6.97,
         7.98, 8.87, 9.77, 10.67, 11.63, 12.65, 13.57, 14.53],
}
SWARAS = {"S": "S", "R": "R2", "G": "G3", "P": "P", "D": "D2"}


def absolute_beat(seconds, attacks):
    if seconds < attacks[0]:
        return (seconds - attacks[0]) / (attacks[1] - attacks[0])
    if seconds > attacks[-1]:
        period = float(np.median(np.diff(attacks)[-4:]))
        return 15 + (seconds - attacks[-1]) / period
    return float(np.interp(seconds, attacks, np.arange(16)))


def build_part(start, end, attacks, tokens, vocal_end):
    origin = absolute_beat(start, attacks)
    points = sorted(set([start, end] + [t for t in attacks if start < t < end]))
    beat_map = [{"onset": round(t - start, 6), "beat": round(absolute_beat(t, attacks) - origin, 6)}
                for t in points]
    boundaries = sorted(set(points + ([vocal_end] if start < vocal_end < end else [])))
    events = []
    for a, b in zip(boundaries, boundaries[1:]):
        note_index = int(np.searchsorted(attacks, a + .000001, side="right")) - 1
        silence = note_index < 0 or a >= vocal_end
        token = None if silence else tokens[min(note_index, 15)]
        events.append({
            "kind": "rest" if silence else "note",
            "swara": None if silence else SWARAS[token.rstrip("'")],
            "octave": 0 if silence else token.count("'"),
            "onset": round(a - start, 6), "duration": round(b - a, 6),
            "cycle_position": round(absolute_beat(a, attacks) % 8, 6),
        })
    return origin % 8, beat_map, events


def build(take):
    folder = ROOT / "data/audio"
    active = json.loads((folder / "annotations.json").read_text())
    if active.get(f"mohanam_take{take}", {}).get("seed_beat_map"):
        raise ValueError(f"Take {take} already has approved timing. Use a new revision for further changes.")
    intake = json.loads((folder / f"mohanam_take{take}_intake.json").read_text())
    attacks = ATTACKS[take]
    tokens = (intake["opening"] + " " + intake["continuation"]).split()
    x = read_audio(ROOT / intake["working_copy"])
    original_hash = hashlib.sha256((ROOT / intake["source"]).read_bytes()).hexdigest()
    if original_hash != intake["source_sha256"]:
        raise ValueError("Source has changed since intake")
    old_start, old_split, end = (intake[key] for key in ("start_seconds", "split_seconds", "end_seconds"))
    start, split = attacks[0], attacks[8]
    cut_paths = {}
    for part, a, b in (("seed", start, split), ("response", split, end), ("combined", start, end)):
        path = folder / f"mohanam_take{take}_timing_{part}_draft.wav"
        content = wav_bytes(x[round(a * RATE):round(b * RATE)])
        if path.exists() and path.read_bytes() != content:
            raise ValueError("Timing review cut already exists with different content; use a new revision")
        if not path.exists():
            path.write_bytes(content)
        cut_paths[part] = path.relative_to(ROOT).as_posix()
    # Take 31's sustained voicing ends near 15.04 s; this tail classification
    # is explicitly part of the review. No approved trim is shortened.
    vocal_end = end if take == 30 else 15.12
    seed_phase, seed_map, seed_events = build_part(start, split, attacks, tokens, vocal_end)
    response_phase, response_map, response_events = build_part(split, end, attacks, tokens, vocal_end)
    average_bpm = 60 * 15 / (attacks[-1] - attacks[0])
    annotation = {
        "approved": False, "level": "note",
        "group_id": f"mohanam_practice_exercise{take - 29:02}",
        "split_group_id": "mohanam_practice_batch01",
        "tonic_hz": intake["tonic_hz_estimate"], "tempo_bpm": round(average_bpm, 3),
        "beats_per_cycle": 8, "seed_start_beat": round(seed_phase, 6),
        "response_start_beat": round(response_phase, 6),
        "seed_beat_map": seed_map, "response_beat_map": response_map,
        "seed_events": seed_events, "response_events": response_events,
        "timing_source": "Proposed spectral-attack beat map; singer timing review pending",
        "notation_source": "Supplied exercise; one swara per self-counted beat",
    }
    # This checks only schema/coverage/mathematics. It is not listening approval.
    durations = {part: len(read_audio(ROOT / cut_paths[part])) / RATE
                 for part in ("seed", "response")}
    validate_annotation({**annotation, "approved": True}, durations)
    click_audio = .85 * x.copy()
    for index, onset in enumerate(attacks):
        a = round(onset * RATE)
        count = min(round(.035 * RATE), len(x) - a)
        t = np.arange(count) / RATE
        hz = 1400 if index % 8 == 0 else 950
        click_audio[a:a + count] += .13 * np.sin(2 * np.pi * hz * t) * np.exp(-t / .008)
    click_path = folder / f"mohanam_take{take}_beat_review.wav"
    audio_bytes = wav_bytes(click_audio)
    if click_path.exists() and click_path.read_bytes() != audio_bytes:
        raise ValueError("Review audio already exists with different markers; use a new revision")
    if not click_path.exists():
        click_path.write_bytes(audio_bytes)
    issues = ["Click 16 separates repeated Sa notes; its exact position needs listening confirmation."]
    if take == 31:
        issues.append("The proposed end of singing at 15.12 s and following tail need confirmation.")
    result = {
        "id": intake["id"], "take": take, "source_sha256": original_hash,
        "source": intake["source"], "working_copy": intake["working_copy"],
        "click_audio": click_path.relative_to(ROOT).as_posix(),
        "self_counted_tala_user_confirmed": True, "timing_approved": False,
        "structure_checked": True, "attacks_seconds": attacks, "tokens": tokens,
        "proposed_cuts": {"start_seconds": start, "split_seconds": split, "end_seconds": end,
                          "previous_start_seconds": old_start, "previous_split_seconds": old_split,
                          "paths": cut_paths},
        "mean_bpm": round(average_bpm, 2),
        "local_bpm_range": [round(float(v), 2) for v in (60 / max(np.diff(attacks)), 60 / min(np.diff(attacks)))],
        "review_focus": issues, "annotation_draft": annotation,
        "caveat": "Proposed markers use syllable attacks, not pitch-settling times. End extrapolation and rest labels are provisional.",
    }
    (folder / f"mohanam_take{take}_timing_draft.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def write_page(results):
    cards = []
    for r in results:
        notes = ''.join(f'<span data-index="{i}">{i % 8 + 1}: {html.escape(token)}</span>'
                        for i, token in enumerate(r["tokens"]))
        cards.append(f'''<section data-take="{r['take']}"><h2>Recording {r['take']}</h2>
<p class="instructions">Play with clicks. Each click should land at the start of a sung swara; the higher clicks mark beats 1 and 9 (the next cycle). Click 9 is also the proposed response start.</p>
<div class="notes">{notes}</div><p class="position">Ready</p>
<label>With proposed beat clicks</label><audio class="marked" controls preload="metadata" src="{Path(r['click_audio']).name}"></audio>
<label>Original recording</label><audio controls preload="metadata" src="{Path(r['working_copy']).name}"></audio>
<details><summary>Hear the proposed phrase cuts separately</summary>
<label>Opening</label><audio controls preload="metadata" src="{Path(r['proposed_cuts']['paths']['seed']).name}"></audio>
<label>Continuation</label><audio controls preload="metadata" src="{Path(r['proposed_cuts']['paths']['response']).name}"></audio></details>
<p><b>Especially check:</b> {html.escape(' '.join(r['review_focus']))}</p>
<details><summary>Proposed times and tempo</summary><p>{html.escape(', '.join(str(t) for t in r['attacks_seconds']))} seconds.</p>
<p>Average {r['mean_bpm']} bpm; intervals vary. These values describe the draft map, not an independent tala measurement.</p></details></section>''')
    payload = json.dumps({str(r['take']): r['attacks_seconds'] for r in results})
    page = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Swaraga — beat alignment check</title><style>
body{max-width:1000px;margin:36px auto;padding:0 20px;font:17px/1.6 system-ui;background:#f7f5ef;color:#193c38}
section{background:white;border:1px solid #d4ded8;border-radius:14px;padding:24px;margin:24px 0}h1{font-size:32px;line-height:1.2}h2{margin-top:0}
audio{width:100%;display:block;margin:8px 0 18px}.notes{display:grid;grid-template-columns:repeat(8,1fr);gap:7px}.notes span{background:#f0f3ee;padding:8px;text-align:center;border-radius:6px}.notes .active{background:#176454;color:white}
label{font-weight:600}.position{min-height:1.6em;color:#52665b}details{font-size:14px}summary{cursor:pointer}@media(max-width:650px){.notes{grid-template-columns:repeat(4,1fr)}}
</style><h1>Does the beat follow your singing?</h1>
<p>You kept tala yourself, so this proposed beat map follows a changing pace. Your earlier review approved phrase cuts; this checks where the individual beats fall.</p>
<p>Listen once to recordings <b>30 and 31 with clicks</b>. Reply “30 timing good, 31 timing good”, or name a click that comes early/late. No need to inspect timestamps or re-record.</p>
<p>The review copies add quiet clicks and lower the voice slightly for headroom. The proposed response cuts move 40 ms earlier in take 30 and 170 ms earlier in take 31, to the detected attacks. Your approved playback files are unchanged. Recording 32 remains in prepared mode while its uncertain alignment is investigated.</p>
CARDS
<script>const times=PAYLOAD;const all=[...document.querySelectorAll('audio')];
for(const a of all)a.addEventListener('play',()=>{for(const b of all)if(a!==b)b.pause();});
for(const section of document.querySelectorAll('section')){const a=section.querySelector('.marked'),markers=times[section.dataset.take],notes=[...section.querySelectorAll('.notes span')];
function update(){let i=-1;for(let j=0;j<markers.length;j++)if(a.currentTime>=markers[j])i=j;
notes.forEach((n,j)=>n.classList.toggle('active',j===i));section.querySelector('.position').textContent=i<0?'Before the first marker':`Proposed cycle ${Math.floor(i/8)+1}, beat ${i%8+1} · ${a.currentTime.toFixed(2)} s`;
if(!a.paused)requestAnimationFrame(update);}a.addEventListener('play',update);a.addEventListener('seeked',update);a.addEventListener('pause',update);}
</script></html>'''.replace('CARDS', ''.join(cards)).replace('PAYLOAD', payload)
    if all(r.get("timing_approved") for r in results):
        page = page.replace("Does the beat follow your singing?", "Beat maps approved")
        page = page.replace("Listen once to recordings <b>30 and 31 with clicks</b>. Reply “30 timing good, 31 timing good”, or name a click that comes early/late. No need to inspect timestamps or re-record.",
                            "You approved the timing for <b>30 and 31</b>. Both are now available for timed playback and retrieval in the main demo. These click overlays remain as review references; the demo uses your voice without clicks.")
    (ROOT / "data/audio/timing_review.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    results = [build(take) for take in ATTACKS]
    write_page(results)
    print(json.dumps([{k: r[k] for k in ("take", "mean_bpm", "local_bpm_range", "structure_checked", "review_focus")}
                      for r in results], indent=2))
