# Hindolam extension

The optional Hindolam review page is available at
<http://127.0.0.1:8765/review/hindolam/> while the app is running. Its audio
assets must be prepared separately; they are not included in a Git clone.

Three instrumental examples each continue a 16-note opening with eight notes,
using the n-gram baseline and Hindolam notation prior. The page supports separate
and combined playback, browser-local listening feedback, and an exportable summary.

## Vocal content status

The archived V1-V3 excerpts contain lyrics and were rejected for swaram-only
retrieval. Their players are hidden, the server refuses their WAV URLs, and
rebuilding preserves the rejection. Hashes and diagnostic files remain for
provenance. There are currently no approved Hindolam vocal examples.

A replacement must contain sung swara syllables throughout the selected interval,
with reviewed transcription and alignment before entering the active bank.
A lesson title, notation sheet, low-energy cut, or successful pitch extraction
does not establish swaram-only content. Instrumental feedback does not approve
vocal material.

## Sources and representation

[Samaja Vara Gamana notation](https://www.shivkumar.org/music/samajavaragamana.htm)
identifies Hindolam, Adi tala, Tyagaraja, and the Peri Sriramamurthy version.
The importer accepted **16 distinct passages, 294 written note attacks**.
It preserves notation punctuation and underlines but learns pitch-class order
only: `S G2 M1 D1 N2`. Octaves, durations and gamakas are not reconstructed.
Two duplicate pitch sequences and one unsupported paragraph were excluded.

The [audio](https://www.shivkumar.org/music/samajavaragamana.mp3) is the archive
rendition, credited to Shivkumar Kalyanaraman following the referenced version.
The [archive author's background and copyright page](https://www.shivkumar.org/music/background.html)
permits copying/distribution for noncommercial use with original authorship
acknowledged. This is custom permission, not a Creative Commons license.
The review page and manifest retain attribution and the permission link.

The notation and all three audio excerpts share composition group
`tyagaraja_samaja_vara_gamana`. They must not be split across training and a
claimed unseen-composition evaluation. These are development listening examples.
Three passages from one performance are not three independent recordings.

## Rejected audio: checks and limitations

Source MP3 and working-audio SHA-256 hashes are recorded. FFmpeg decodes the MP3
to **float32 mono at 24 kHz** first; one shared gain is applied before PCM export
to avoid clipping reconstructed peaks above nominal full scale. No retuning,
time stretching, denoising or voice synthesis is applied.

Cuts are proposed near low-energy positions in three well-separated regions.
The outer edges receive 8 ms fades. The middle split is continuous; concatenated
PCM bytes from each opening/continuation equal the combined clip exactly.
Low-energy cuts do not prove musical phrase boundaries; that is a review question.
Diagnostic pitch tracks use a 70–500 Hz YIN-like estimator. Confidence and median
F0 are descriptive; the median is **not** labelled as tonic. Drone/voice confusion
is possible, and no note/beat annotation is promoted from these tracks.

The original checks covered source hashes, audio decoding, duration, output levels, contiguous
joins, raga pitch membership, deterministic generation, repeated-note preference,
source grouping, review gating, and local HTTP asset restrictions. Human musical
quality, sung syllable content and precise tala alignment remain outside these
automated checks. Passing them did not make the vocal sources suitable.


## Optional Saraga metadata

The source-fetching script also supports Saraga metadata. No Saraga audio is
included. The metadata investigation identified Chaitra Sairam's Hindolam
performance of Govardhana Girisham (Rupaka), but audio/pitch downloads were
blocked by the upstream host. Its tonic and timestamps are not applied to the
separate archive rendition. Source recordings must retain their own alignment
and provenance; the optional live download path remains unverified.

## Reproduction and files

```powershell
python scripts/fetch_hindolam_sources.py
ffmpeg -v error -n -i .demo-artifacts/hindolam-sources/samajavaragamana.mp3 -ac 1 -ar 24000 -f f32le .demo-artifacts/hindolam-sources/samajavaragamana.f32
python scripts/prepare_hindolam_review.py
python -m pytest -q -p no:cacheprovider tests/test_hindolam.py tests/test_knowledge.py tests/test_demo.py tests/test_models.py tests/test_decode.py
python scripts/run_demo.py
```

FFmpeg's `-n` refuses an existing working copy. Reuse an existing verified copy
when rerunning preparation. The importer pins the notation hash after the first
import and refuses changed audio/approved review data. Review feedback does not
automatically change any production approval flag. Rerunning recreates rejected
vocal artifacts for audit only, and cannot restore them to the listening queue.

- `data/knowledge/hindolam_sources.json`: notation provenance and source hash.
- `data/knowledge/hindolam_notation.json`: parsed passages and retained source spans.
- `data/audio/hindolam_review/review.json`: source provenance, cuts, hashes,
  generated notes, pending status and diagnostic summaries.
- `data/audio/hindolam_review/*.wav`: 18 playback files (three parts per example).
- `data/audio/hindolam_review/*-pitch.npz`: three unapproved diagnostic F0 tracks.
- `reports/hindolam_review_checks.json`: technical preparation report.
- `src/swaraga/hindolam.py`: Hindolam generator used by the review preparation.

The source MP3 and float working copy live in the ignored local cache. The
snapshot packager includes prepared clips, provenance, review assets and notation.
