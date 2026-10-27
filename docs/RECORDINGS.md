# Adding Ishita's recordings

The catalog now contains six prepared pairs: three from Ishita's Ninnu Kori
take 29 and one each from practice takes 30, 31 and 32. Ishita reviewed all six
cuts/joins and said they were good. She subsequently approved the note/beat
markers and refined boundaries for 30 and 31; these now support timed playback
and retrieval between the two exercises. The remaining four entries' annotations
use `level: "phrase"` and `approved_for: "prepared_playback"`: this approval
covers prepared playback with supplied phrase notation, not note timestamps,
octave labels, tempo, or tala phase. No timed highlighting is shown for those
four phrase-only entries. The Ninnu
Kori pairs overlap within one source group. The practice batch stays grouped
together for splitting because its exercises share material. All six are
bank-only examples; only 30 and 31 currently qualify as timed retrieval candidates.

Phrase-level annotations require `approved`, `group_id`, `shruti_label`,
`seed_notation`, `response_notation`, and `review_scope`. They must not contain
event/tala timing fields. The detailed timing workflow below applies when
adding fully timed recordings; it is not required for phrase-only playback.

Only the technical owner needs this document; Ishita can send originals and
the simple notes from `SUBMISSION_TODO.md`.

## Practice batch received and approved

This batch uses Mohanam, Adi tala, and Ishita's G# / 5.5 shruti. It contains
three simple practice exercises written for the demo, each with one opening
cycle and one continuation cycle. They add contexts outside Ninnu Kori.

Use 60 bpm if comfortable, one swara per beat, eight beats per cycle; keep the
same tempo across all three. Each pair lasts about 16 seconds, plus lead-in and
tail. Sing continuously across the arrow. S' means upper Sa; all other notes
are in the middle octave. R/G/D denote Mohanam's R2/G3/D2.

| File | Opening (8 beats) | Continuation (8 beats) |
| --- | --- | --- |
| `mohanam_practice01` | S R G P G R S R | G P D P G R S S |
| `mohanam_practice02` | G P D S' D P G R | S R G P G R S S |
| `mohanam_practice03` | S G R S R G P G | P D P G R G R S |

The rows above were received as `Standard recording 30.mp3`, `31.mp3` and
`32.mp3`, respectively. Ishita approved the prepared cuts and joins. Copies
named `mohanam_take30/31/32_seed.wav` and `_response.wav` are byte-identical to
the reviewed drafts; `_cuts.json` files retain source hashes and timestamps.
Detailed timing and tala alignment still need verification before retrieval.
No additional recordings are needed for the current prepared-demo milestone.

## Timing review for self-counted tala

Ishita confirmed that takes 30-32 follow her own tala count, not a metronome.
`scripts/prepare_timing_review.py` prepares draft beat maps for 30 and 31 from
inspected spectral attacks. Pitch settling is not used as the syllable onset.
The review is `data/audio/timing_review.html`, with added-click WAVs and proposed
cuts at the ninth attack. These move the response starts 40 ms earlier for 30
and 170 ms earlier for 31. The six approved prepared examples remain unchanged.

Ishita confirmed both timing reviews are good, including the response-start
marker and the repeated ending Sas. Approved records are saved separately as
`mohanam_take30_timing.json` and `mohanam_take31_timing.json`; original draft
records remain archived. The active catalog uses the `_timed_seed.wav` and
`_timed_response.wav` copies, with approved annotations in `annotations.json`.
Review clicks are not included in playback. Take 32 retains phrase-only playback.

The validator, retrieval phase check, and UI now support optional
`seed_beat_map` / `response_beat_map` arrays. Each anchor has `onset` in seconds
and `beat` as elapsed beats from the start of that clip. Both maps must cover
their clips exactly, increase strictly, and imply 20-300 bpm between anchors.
Event cycle positions and joins use interpolation through this map. Without
maps, existing constant-tempo annotations behave as before. `tempo_bpm` is a
summary average when maps are present, not a fixed playback clock.

The timed annotations identify each practice exercise as its own retrieval `group_id`, with
the broader `split_group_id: "mohanam_practice_batch01"` retained to prevent
related exercises entering both bank and evaluation. The three overlapping
Ninnu Kori pairs remain one source group. No independent evaluation result is
claimed. Draft timing annotations are not loaded by the main recording bank.
Retrieval checks pass in both directions, 30 to 31 and 31 to 30. This is one
alternative per query, not a test of ranking quality across a large candidate bank.

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
