# Recording integration

Swaraga plays existing vocal recordings through a catalog and reviewed annotation
file. Audio is excluded from Git. A fresh clone supports generated swaras;
recorded playback requires restoring the catalog's WAV files or registering
your own recordings. Use audio you are authorized to use and preserve attribution.

The reference catalog contains six Mohanam/Adi pairs from four source takes.
Two have reviewed note/beat annotations and can retrieve each other's responses.
The other four are phrase-only prepared examples. Related crops remain in the
same dataset split; these recordings are not an independent evaluation set.

## Phrase-only playback

For a reviewed pair without note-level timing, set `level: "phrase"`,
`approved: true`, and `approved_for: "prepared_playback"`. Supply `group_id`,
`shruti_label`, `seed_notation`, `response_notation`, and `review_scope`.
Do not include event or tala timing fields in a phrase-only annotation. These
entries support prepared playback, not timed highlighting or retrieval.

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

M4A/MP3 conversion requires **FFmpeg on PATH**. MP3 conversion has been
verified; the M4A path has not yet been exercised. Subsequent cuts use the
decoded PCM WAV working copy. Source hashes and conversion metadata are
retained in the intake records.

## 2. Register the recording

Add real dictionaries to `RECORDINGS` in `team_tasks/recording_catalog.py`.
All eight fields are required.

| Field | Meaning |
| --- | --- |
| `id` | Unique letters, digits, underscores or hyphens |
| `title` | Short display label |
| `raga`, `tala` | Exact supplied musical names |
| `seed_path`, `response_path` | Relative paths inside `data/audio/`, with `.wav` extension |
| `source_take` | Original take identity, shared by all crops from that take |
| `split` | `bank` or `evaluation`, assigned by the dataset maintainer |

Keep all takes/crops from the same composition or seed family in one split.
The technical annotation's `group_id` enforces this more broadly than take ID.
Never put the same material into both splits under different filenames.

## 3. Add reviewed timing annotations

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
Without beat maps, timing is derived from constant tempo. For expressive
timing, supply reviewed beat maps as described below.
Gamakas remain in the original audio; these events are coarse swara labels,
not a reconstruction of its pitch trajectory.

## 4. Validate and restart

```powershell
python scripts/check_demo.py
python scripts/run_demo.py
```

Restart the app after catalog or annotation edits. Invalid or
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


## Variable-tempo beat maps

For reviewed expressive timing, provide both `seed_beat_map` and
`response_beat_map`. Each is an array of anchors with `onset` in clip-relative
seconds and `beat` in elapsed beats. Both maps must start at onset/beat zero,
cover their clips exactly, increase strictly, and imply 20-300 bpm between
anchors. Event cycle positions and join checks interpolate through these maps.
`tempo_bpm` remains a summary average; it is not the playback clock when maps
are present. Keep draft annotations separate from `annotations.json`.

Use `split_group_id` when multiple retrieval groups share related source
material. It prevents related exercises entering both bank and evaluation
while allowing distinct exercises to be considered as retrieval candidates.

## Export and package

Listen to prepared and retrieved phrases before approving them. The automated
checker verifies technical integrity, not musical quality or recording rights.
Download complete WAVs in the app, or run `python scripts/check_demo.py` for
backups. It exits nonzero while catalog audio is missing or invalid.

`python scripts/package_demo.py` creates a local source/audio ZIP after a
successful check. It includes audio under `data/audio/`, even though those files
are ignored by Git. It excludes original-recording backups and personal notes.
Keep originals separately and review the ZIP before distributing it.
