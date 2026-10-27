# Hindolam listening review

Prepared 2026-10-27. Open <http://127.0.0.1:8765/review/hindolam/> after starting
`python scripts/run_demo.py`.

## Correction after Ishita's content review

- **V1–V3 are rejected.** Ishita identified lyric content: these are not the
  swaram-only vocals required for this pipeline. The page omits their players
  and review controls, the server refuses their WAV URLs, and rebuilding retains
  their rejected status. Files and hashes remain only for audit provenance.
- G1–G3: three deterministic Hindolam instrumental continuations, 16 seed notes
  followed by 8 generated notes, using the established n-gram baseline plus the
  new Hindolam notation prior.
- A page with combined and separate playback, optional per-example feedback,
  browser-local persistence, and a copy-to-chat summary.

The active approved vocal bank remains separate from pending review assets.
No Ishita approval, exact vocal transcription or tala alignment has been inferred.
The vocal pipeline is incomplete. A replacement needs sung swara syllables
throughout each selected excerpt, with no sahitya, spoken instruction, or
non-swara singing. A title, notation sheet, low-energy boundary or successful
pitch extraction does not verify that condition. Record the evidence for the
exact source intervals before setting `swara_only_verified: true`; then prepare
transcription/alignment and request final listening review. The instrumental
examples remain optional to review and cannot approve vocal content.

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

## Saraga investigation

The downloaded MTG metadata archive contains one exact Hindolam match:
Chaitra Sairam's **Govardhana Girisham**, Rupaka, MBID
`93f38e28-f411-4b06-9494-91232649a635`. Its tonic value and 83 manually annotated
sama timestamps were obtained. Two substring matches were Margahindolam and
excluded. The selected recording's audio/pitch download was blocked by Zenodo
HTTP 403, reporting unusual traffic from this network.

**None of those Saraga timestamps or tonic values are applied to the archive
rendition.** The fallback has its own source hash, cuts and analysis. The optional
Saraga downloader remains available, but its live range-download path has not
succeeded here. No Saraga audio is included in this review.

## Replacement source search (unverified candidates)

The archive separates the [Samaja Vara Gamana lesson](https://www.shivkumar.org/music/samajavaragamana-detailed.mp3)
from the rejected rendition. Its lesson label alone does not prove swaram-only
content or identify safe intervals; exact vocal content has not been checked.
The [manodharma index](https://www.shivkumar.org/music/manodharma/index.html)
also explicitly lists two Hindolam swarakalpana recordings by Semmangudi
Srinivasa Iyer:

- [Govardhana, Tisai 1960](https://www.shivkumar.org/music/manodharma/ragas/hindolam/08c-govardhana-hindolam-swarakalpana-ssi-tisai1960.mp3)
- [Govardhana, C12](https://www.shivkumar.org/music/manodharma/ragas/hindolam/22b_FILLER_govardhana_hindolam-swarakalpana-ssi-c12.mp3)

These are discovery leads, not accepted audio. The web reader could resolve
the links but could not fetch their MP3 content. Swarakalpana passages may return
to lyrics; the whole track cannot be assumed swaram-only. No exact intervals or
syllable transcription have been verified. The archive author's permission for
his own rendition must not be assumed to cover these third-party performances.
No replacement has been promoted or sent for listening approval.

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
