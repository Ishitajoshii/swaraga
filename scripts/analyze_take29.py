"""Reproduce a provisional, notation-guided analysis of Ishita's take 29.

Uses NumPy only. This is an offline review aid, not automatic musical approval.
It never changes the source audio, catalog, or approved annotations.
"""
from pathlib import Path
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.audio import RATE, read_audio, wav_bytes

OUT = ROOT / ".demo-artifacts/take29"
SOURCE = ROOT / "data/audio/ninnu_kori_take29_review.wav"
REFERENCE = ROOT / "data/audio/ninnu_kori_take29_notation.json"
DEGREES = {"S": 0, "R": 2, "G": 4, "P": 7, "D": 9}


def pitch_track(samples):
    # Low-pass before downsampling 24 kHz -> 8 kHz; 80 ms frames, 20 ms hop.
    taps = np.arange(-48, 49)
    kernel = np.sinc(taps / 3) * np.hamming(len(taps))
    kernel /= kernel.sum()
    x = np.convolve(samples, kernel, mode="same")[::3]
    rows = []
    for offset in range(0, len(x) - 640, 160):
        frame = x[offset:offset + 640]
        frame = frame - frame.mean()
        windows = np.lib.stride_tricks.sliding_window_view(frame, 320)
        difference = np.sum((windows[1:55] - frame[:320]) ** 2, axis=1)
        cumulative = difference * np.arange(1, 55) / np.maximum(np.cumsum(difference), 1e-15)
        # Broad 150-500 Hz voice range, independent of the target swaras.
        choices = [k for k in range(15, 53) if cumulative[k] < .2
                   and cumulative[k] <= cumulative[k - 1] and cumulative[k] < cumulative[k + 1]]
        k = choices[0] if choices else int(np.argmin(cumulative[15:53])) + 15
        denominator = cumulative[k - 1] - 2 * cumulative[k] + cumulative[k + 1]
        shift = np.clip(.5 * (cumulative[k - 1] - cumulative[k + 1]) / denominator, -.5, .5) if denominator else 0
        rows.append(((offset + 320) / 8000, 8000 / (k + 1 + shift),
                     np.clip(1 - cumulative[k], 0, 1), np.sqrt(np.mean(frame ** 2))))
    return np.array(rows)


def reference_notes():
    notes = []
    reference = json.loads(REFERENCE.read_text(encoding="utf-8"))
    for section in reference["sections"]:
        for line_index, line in enumerate(section["lines"]):
            phrase = f"Pallavi line {line_index + 1}" if section["name"] == "Pallavi" else section["name"]
            for token in line.replace("|", " ").replace("-", " ").split():
                if token == ",":
                    notes[-1]["units"] += 1
                else:
                    notes.append({"swara": token, "units": 1, "phrase": phrase})
    return notes


def align(track, notes, tonic):
    voiced = (track[:, 2] > .75) & (track[:, 3] > .015)
    active = np.flatnonzero(voiced)
    if not len(active):
        raise ValueError("No reliable voiced frames; manual analysis is required")
    first, last = max(0, active[0] - 2), min(len(track), active[-1] + 3)
    data = track[first:last]
    pitches = 12 * np.log2(data[:, 1] / tonic)
    good = (data[:, 2] > .75) & (data[:, 3] > .015)
    total_units = sum(note["units"] for note in notes)
    unit_frames = len(data) / total_units
    previous = np.full(len(data) + 1, np.inf)
    previous[0] = 0
    back = []
    for note in notes:
        distance = np.abs((pitches - DEGREES[note["swara"]] + 6) % 12 - 6)
        cost = np.where(good, np.minimum(distance, 3) ** 2, .35)
        prefix = np.r_[0, np.cumsum(cost)]
        expected = unit_frames * note["units"]
        current = np.full_like(previous, np.inf)
        pointer = np.zeros(len(previous), dtype=int)
        for duration in range(max(6, int(expected * .4)), int(expected * 1.9) + 1):
            ends = np.arange(duration, len(previous))
            # Soft rhythm prior; repeated identical notes are not independently detected.
            value = (previous[ends - duration] + prefix[ends] - prefix[ends - duration]
                     + 6 * ((duration - expected) / expected) ** 2)
            better = value < current[ends]
            chosen = ends[better]
            current[chosen] = value[better]
            pointer[chosen] = duration
        back.append(pointer)
        previous = current
    if not np.isfinite(previous[-1]):
        raise ValueError("No complete alignment under the duration bounds")
    end = len(data)
    spans = []
    for note, pointer in zip(reversed(notes), reversed(back)):
        start = end - int(pointer[end])
        segment = data[start:end]
        strong = segment[(segment[:, 2] > .8) & (segment[:, 3] > .015)]
        relative = 12 * np.log2(strong[:, 1] / tonic) if len(strong) else np.array([])
        octave = int(np.rint(np.median((relative - DEGREES[note["swara"]]) / 12))) if len(relative) else None
        residual = np.abs((relative - DEGREES[note["swara"]] + 6) % 12 - 6)
        agreement = float(np.mean(residual < .8)) if len(relative) else 0
        spans.append({**note, "start_seconds": round(float(segment[0, 0] - .01), 3),
                      "end_seconds": round(float(segment[-1, 0] + .01), 3),
                      "octave_estimate": octave,
                      "voiced_fraction": round(len(strong) / len(segment), 3),
                      "pitch_agreement_fraction": round(agreement, 3),
                      "review_needed": agreement < .65 or len(strong) / len(segment) < .55})
        end = start
    if end != 0:
        raise ValueError("Incomplete backtrace")
    return list(reversed(spans))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    samples = read_audio(SOURCE)
    track = pitch_track(samples)
    np.savetxt(OUT / "pitch.csv", track, delimiter=",", header="seconds,hz,periodicity,rms", comments="")
    # The user supplied G#; estimate detuning from voiced frames near Mohanam degrees.
    reference_tonic = 440 * 2 ** ((56 - 69) / 12)  # G#3, an octave convention.
    good = track[(track[:, 2] > .85) & (track[:, 3] > .025)]
    relative = 12 * np.log2(good[:, 1] / reference_tonic)
    error = (relative[:, None] - np.array(list(DEGREES.values())) + 6) % 12 - 6
    closest = error[np.arange(len(error)), np.argmin(np.abs(error), axis=1)]
    central = closest[np.abs(closest) < .5]
    tonic = reference_tonic * 2 ** (float(np.median(central)) / 12)
    spans = align(track, reference_notes(), tonic)
    phrases = []
    for span in spans:
        if not phrases or phrases[-1]["label"] != span["phrase"]:
            phrases.append({"label": span["phrase"], "start_seconds": span["start_seconds"],
                            "end_seconds": span["end_seconds"]})
        else:
            phrases[-1]["end_seconds"] = span["end_seconds"]
    # Expose any long lead-in to a phrase separately instead of calling it sung.
    for phrase in phrases:
        region = track[(track[:, 0] >= phrase["start_seconds"]) & (track[:, 0] < phrase["end_seconds"])]
        reliable = region[(region[:, 2] > .8) & (region[:, 3] > .015)]
        phrase["first_reliable_pitch_seconds"] = round(float(reliable[0, 0]), 3) if len(reliable) else None
    review_pairs = []
    for index in range(3):
        start = phrases[index]["start_seconds"]
        split = phrases[index]["end_seconds"]
        end = phrases[index + 1]["end_seconds"]
        name = f"ninnu_kori_take29_pair{index + 1}_draft.wav"
        path = ROOT / "data/audio" / name
        content = wav_bytes(samples[round(start * RATE):round(end * RATE)])
        if path.exists() and path.read_bytes() != content:
            raise ValueError(f"Refusing to replace a different review clip: {path}")
        path.write_bytes(content)
        review_pairs.append({"label": f"Pallavi lines {index + 1} and {index + 2}",
                             "path": path.relative_to(ROOT).as_posix(),
                             "start_seconds": start, "split_seconds": split, "end_seconds": end,
                             "note": "Original adjacent phrases; draft cut, not a generated response or retrieval result."})
    analysis = {
        "source": SOURCE.relative_to(ROOT).as_posix(), "approved": False,
        "method": "Local YIN-style pitch estimates plus duration-constrained, notation-guided alignment",
        "tonic_hz_estimate": round(tonic, 3), "tonic_octave_convention": "G#3 as middle Sa",
        "tempo_bpm": None, "beats_per_cycle": None,
        "limitations": [
            "Not independently transcribed: the supplied note order constrains the alignment.",
            "Repeated-note boundaries use a duration prior and need listening review.",
            "Gamakas, breaths and background sound can reduce pitch agreement.",
            "Low periodicity is not proof of silence; no rest events are inferred.",
            "Tala subdivision, cycle phase and tempo are unverified; no tala timing is claimed.",
            "No listening approval has been performed; these are draft estimates."
        ],
        "phrases": phrases, "notes": spans, "review_pairs": review_pairs
    }
    (ROOT / "data/audio/ninnu_kori_take29_alignment_draft.json").write_text(json.dumps(analysis, indent=2) + "\n", encoding="utf-8")
    write_review(analysis, track)
    print(json.dumps({"tonic_hz_estimate": analysis["tonic_hz_estimate"], "phrases": phrases,
                      "notes": len(spans), "notes_flagged": sum(s["review_needed"] for s in spans)}, indent=2))


def write_review(analysis, track):
    """A local, playable review page; never publishes these drafts to the demo."""
    payload = json.dumps({**analysis, "pitch": track[::2].round(4).tolist()}).replace("<", "\\u003c")
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ninnu Kori — recording review</title>
<style>
body{max-width:1050px;margin:40px auto;padding:0 20px;font:17px/1.55 system-ui;color:#182b30;background:#f8f6f0}
h1{font-size:32px;margin-bottom:5px}h2{font-size:23px}p{max-width:850px}
.tag{color:#854800;font-weight:600}.card{background:white;border:1px solid #d5dcda;border-radius:12px;padding:20px;margin:18px 0}
audio{display:block;width:100%;margin:14px 0}button{cursor:pointer;padding:9px 15px;border:1px solid #345e60;border-radius:7px;background:#edf6f2;color:#182b30;margin:4px}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{text-align:left;padding:8px;border-bottom:1px solid #e1e5e3}
.current{background:#dceee6}.uncertain{color:#915200}svg{width:100%;height:auto;background:#fff}small{color:#536467}
</style>
<h1>Ninnu Kori · your recording</h1><div class="tag">Draft alignment · listening review pending</div>
<p>Full pallavi and the opening G , G , P , , , of the anupallavi. Swaras only, Mohanam, G♯ / 5.5 shruti.
The note order comes from your notation; the timing and octaves below are estimates from the recording.</p>
<div class="card"><h2>Original performance</h2><audio id="player" controls preload="metadata" src="ninnu_kori_take29_review.wav"></audio>
<p id="now">Play the recording to follow the draft notes.</p><div id="phrases"></div>
<small>The final fragment's first reliable pitched frame is shown separately from its estimated boundary. Background sound and breaths are not automatically labelled silence.</small></div>
<div class="card"><h2>Three prepared pairs to review</h2><p>Each pair uses two adjacent phrases from this same take. They overlap and are not independent examples. The continuation is your existing performance.</p><div id="pairs"></div></div>
<div class="card"><h2>Measured pitch and estimated notes</h2><p>Blue dots show reliable pitch estimates. Orange lines show the notation alignment. Gaps mean uncertain pitch, not necessarily silence. Click a plot to seek.</p><div id="plots"></div></div>
<div class="card"><h2>Draft swara timings</h2><p>Amber rows need particular attention. All timings remain provisional; repeated swaras use a rhythm estimate. Commas extend the preceding note.</p>
<table><thead><tr><th>Play</th><th>Swara</th><th>Octave estimate</th><th>Time (s)</th><th>Pitch agreement*</th></tr></thead><tbody id="notes"></tbody></table>
<small>*Fraction of reliable pitch frames within 0.8 semitones of the notated swara. This is not a musical-quality score or a calibrated confidence.</small></div>
<p>No tala animation is assigned yet: tempo, subdivision and cycle phase need verification. These clips have not been added to the approved demo bank.</p>
<script>
const data=PAYLOAD;
const player=document.getElementById('player');let stopAt=null;
function playPart(start,end){player.pause();player.currentTime=start;stopAt=end;player.play().catch(()=>{});}
function button(text,start,end){const b=document.createElement('button');b.textContent=text;b.onclick=()=>playPart(start,end);return b;}
for(const p of data.phrases){const row=document.createElement('div');row.append(button(p.label,p.start_seconds,p.end_seconds));
const s=document.createElement('small');s.textContent=` ${p.start_seconds.toFixed(2)}–${p.end_seconds.toFixed(2)} s`;
if(p.first_reliable_pitch_seconds-p.start_seconds>.3)s.textContent+=` · first reliable pitch ${p.first_reliable_pitch_seconds.toFixed(2)} s`;row.append(s);document.getElementById('phrases').append(row);}
for(const p of data.review_pairs){const row=document.createElement('div');const h=document.createElement('strong');h.textContent=p.label;row.append(h);
row.append(button('Opening',p.start_seconds,p.split_seconds),button('Continuation',p.split_seconds,p.end_seconds),button('Together',p.start_seconds,p.end_seconds));
const a=document.createElement('a');a.href=p.path.split('/').pop();a.download='';a.textContent='Download WAV';row.append(a);document.getElementById('pairs').append(row);}
const rows=[];for(const [i,n] of data.notes.entries()){const tr=document.createElement('tr');if(n.review_needed)tr.className='uncertain';
const play=document.createElement('td');play.append(button('▶',n.start_seconds,n.end_seconds));tr.append(play);
for(const value of [n.swara+(n.units>1?' '+','.repeat(n.units-1):''),n.octave_estimate===null?'Uncertain':n.octave_estimate,`${n.start_seconds.toFixed(2)}–${n.end_seconds.toFixed(2)}`,`${Math.round(n.pitch_agreement_fraction*100)}%`]){const td=document.createElement('td');td.textContent=value;tr.append(td);}
rows.push(tr);document.getElementById('notes').append(tr);}
player.addEventListener('timeupdate',()=>{if(stopAt!==null&&player.currentTime>=stopAt){player.pause();stopAt=null;}
const index=data.notes.findIndex(n=>player.currentTime>=n.start_seconds&&player.currentTime<n.end_seconds);
rows.forEach((r,i)=>r.classList.toggle('current',i===index));document.getElementById('now').textContent=index<0?'Outside the draft note boundaries.':`${data.notes[index].phrase} · ${data.notes[index].swara} · ${player.currentTime.toFixed(2)} s (estimated)`;});
player.addEventListener('seeking',()=>{if(stopAt!==null&&player.currentTime>stopAt)stopAt=null;});
const ns='http://www.w3.org/2000/svg';function el(tag,attrs){const e=document.createElementNS(ns,tag);for(const [k,v]of Object.entries(attrs))e.setAttribute(k,v);return e;}
for(const [lo,hi]of [[0,14],[14,28],[28,40.176]]){const svg=el('svg',{viewBox:'0 0 1000 220',role:'img','aria-label':`Pitch from ${lo} to ${hi} seconds`});
const x=t=>45+(t-lo)/(hi-lo)*940,y=s=>180-(s+4)/18*160;
for(const [s,label]of [[-3,'D↓'],[0,'S'],[2,'R'],[4,'G'],[7,'P'],[9,'D'],[12,'S↑']]){svg.append(el('line',{x1:45,x2:985,y1:y(s),y2:y(s),stroke:'#e5e8e6'}));const t=el('text',{x:4,y:y(s)+4,'font-size':12});t.textContent=label;svg.append(t);}
for(const t of [lo,(lo+hi)/2,hi]){const label=el('text',{x:x(t),y:210,'text-anchor':'middle','font-size':12});label.textContent=t.toFixed(1)+' s';svg.append(label);}
for(const [t,hz,confidence,rms]of data.pitch){if(t<lo||t>hi||confidence<.75||rms<.015)continue;const s=12*Math.log2(hz/data.tonic_hz_estimate);svg.append(el('circle',{cx:x(t),cy:y(s),r:1.5,fill:'#397aaa'}));}
for(const n of data.notes){if(n.end_seconds<lo||n.start_seconds>hi||n.octave_estimate===null)continue;const s=({S:0,R:2,G:4,P:7,D:9}[n.swara])+12*n.octave_estimate;svg.append(el('line',{x1:x(Math.max(lo,n.start_seconds)),x2:x(Math.min(hi,n.end_seconds)),y1:y(s),y2:y(s),stroke:'#b86a10','stroke-width':2}));}
svg.onclick=e=>{const rect=svg.getBoundingClientRect();const t=lo+(((e.clientX-rect.left)/rect.width*1000-45)/940)*(hi-lo);player.currentTime=Math.max(0,Math.min(40.176,t));stopAt=null;};document.getElementById('plots').append(svg);}
</script></html>'''.replace('PAYLOAD', payload)
    (ROOT / "data/audio/ninnu_kori_take29_review.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    main()
