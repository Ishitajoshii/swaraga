# Adding Ishita's recordings

The catalog now contains three prepared pairs from Ishita's Ninnu Kori take.
Ishita reviewed all three cuts/joins and said they were good. Their annotations
use `level: "phrase"` and `approved_for: "prepared_playback"`: this approval
covers prepared playback with supplied phrase notation, not note timestamps,
octave labels, tempo, or tala phase. No timed highlighting is shown. The three
pairs overlap within one source group and cannot be used as independent
evaluation examples or retrieval candidates.

Phrase-level annotations require `approved`, `group_id`, `shruti_label`,
`seed_notation`, `response_notation`, and `review_scope`. They must not contain
event/tala timing fields. The detailed timing workflow below applies when
adding fully timed recordings; it is not required for phrase-only playback.

Only the technical owner needs this document; Ishita can send originals and
the simple notes from `SUBMISSION_TODO.md`.

## 1. Keep originals, trim copies

Keep `recordings_originals/` backed up outside the repository too. From the
repository directory, using the actual cut times in seconds:

```powershell
python scripts/prepare_audio.py recordings_originals/take01.wav --id mohanam_seed01_optionA --start 0.5 --split 8.5 --end 12.5
```

This writes seed and response PCM WAVs under `data/audio/`, plus a `_cuts.json`
record with the original path, timestamps, input peak, and possible-clipping
flag. Existing outputs are never overwritten. Originals are unchanged. Use a
new clip ID for a revised cut. Files longer than 10 minutes must be split first.

WAV input supports uncompressed 8/16/24/32-bit integer PCM, mono or multichannel.
Playback copies are mono, 24 kHz, 16-bit PCM. Resampling uses linear interpolation;
inspect the actual recording before accepting the result. Level handling only
attenuates peaks above 0.95; it does not boost quiet noise, denoise, correct
clipping, pitch-shift, or stretch time. Seed and response get the same gain.

M4A/MP3 conversion is supported **when FFmpeg is on PATH**. The MP3 conversion
path has now been exercised with `Standard recording 29.mp3`; its original
hash and conversion metadata are in `data/audio/ninnu_kori_take29_intake.json`.
The installed Windows FFmpeg needed access outside the sandbox. M4A conversion
has not yet been exercised. Subsequent cuts use the decoded PCM WAV working copy.

## 2. Friend 2 enters the simple catalog

Add real dictionaries to `RECORDINGS` in `team_tasks/recording_catalog.py`.
All eight fields are required; retain the function TODO for Friend 2.

| Field | Meaning |
| --- | --- |
| `id` | Unique letters, digits, underscores or hyphens |
| `title` | Short display label |
| `raga`, `tala` | Exact supplied musical names |
| `seed_path`, `response_path` | Relative paths inside `data/audio/`, with `.wav` extension |
| `source_take` | Original take identity, shared by all crops from that take |
| `split` | `bank` or `evaluation`, assigned by the technical owner |

Keep all takes/crops from the same composition or seed family in one split.
The technical annotation's `group_id` enforces this more broadly than take ID.
Never put the same material into both splits under different filenames.

## 3. Technical owner adds timing annotations

`data/audio/annotations.json` is an object keyed by catalog ID. Each entry needs:

| Field | Meaning |
| --- | --- |
| `approved` | Set `true` only after listening and annotation review |
| `group_id` | Same ID for every crop/option/take from one composition or seed family |
| `tonic_hz` | Checked tonic frequency, not a guessed value |
| `tempo_bpm` | Beats per minute; one beat means one tala akshara throughout these annotations |
| `beats_per_cycle` | Number of these beats in a cycle, e.g. 8 for the chosen Adi convention |
| `seed_start_beat`, `response_start_beat` | Zero-based phase in the cycle; include pickups accurately |
| `seed_events`, `response_events` | Ordered events relative to each trimmed clip |

An event contains `kind`, `swara`, `octave`, `onset`, `duration`, and
`cycle_position`. Onsets and durations are seconds; cycle position is zero-based
beats. `kind` is `note`, `hold`, or `rest`. A hold extends the same pitch as the
preceding event; a rest has `swara: null`. Every event has an integer `octave`
(-2 through 2); use 0 for rests. Use explicit variants such as `R2`, `G3`, `D2`.

Illustrative annotation for a **hypothetical** 1-second Sa seed and 1-second Pa
response at 60 bpm (do not add this as a real recording):

```json
{
  "example_only": {
    "approved": true,
    "group_id": "seed_family_01",
    "tonic_hz": 240,
    "tempo_bpm": 60,
    "beats_per_cycle": 8,
    "seed_start_beat": 0,
    "response_start_beat": 1,
    "seed_events": [
      {"kind": "note", "swara": "S", "octave": 0, "onset": 0, "duration": 1, "cycle_position": 0}
    ],
    "response_events": [
      {"kind": "note", "swara": "P", "octave": 0, "onset": 0, "duration": 1, "cycle_position": 1}
    ]
  }
}
```

Annotate silence explicitly, including lead-in/tail silence; events must cover
each clip without overlaps (40 ms tolerance). Cycle phase is checked against
tempo/onset (0.12 beat tolerance), and paired clips must join within 0.15 beats.
This is a constant-tempo, manually annotated demo. Expressive timing requires
careful annotation or a later variable-tempo extension; do not fake alignment.
Gamakas remain in the original audio; these events are coarse swara labels,
not a reconstruction of its pitch trajectory.

## 4. Validate and restart

```powershell
python scripts/check_demo.py
python scripts/run_demo.py
```

Restart the app after catalog/annotation/friend-file edits. Invalid or
unapproved entries are excluded and reported. Cross-split group/take leakage
blocks the entire recording bank until corrected. Missing or corrupt audio is
reported instead of becoming a selectable recording.

Prepared mode plays an approved bank pair. Retrieval can use a bank or evaluation
seed as its query, but only bank responses are candidates. It excludes the query's
group/take, requires matching raga/tala/meter, tonic within 25 cents, tempo within
3%, and compatible join phase. It ranks normalized annotated pitch contours plus
a duration penalty, with ID tie-breaking. Lower distance is closer, **not a
probability or musical-quality score**. No match produces a clear empty result.

The complete WAV concatenates the selected seed and response without crossfade.
Listen for clicks, mismatched loudness, inappropriate melodic joins, and timing
errors; passing structural validation does not establish musical quality.

## 5. Review, export, package

- Listen to three showcase pairs, confirm the displayed notes, and approve them.
- Download the complete WAVs in the app and keep a separate backup.
- Record team listening feedback in `docs/SUBMISSION_NOTES.md`.
- Run `python scripts/package_demo.py` to make a local snapshot; real audio
  under `data/audio/` is included even though it is ignored by Git.
- Save originals and the final demo video separately; the package excludes originals.
