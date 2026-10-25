# Submission working notes

Status: pre-recording implementation, 25 October 2026. This is supporting
material for the report and rehearsal, not a claim that the final vocal demo
or presentation is finished.

## Problem and implemented scope

Swaraga explores short Carnatic phrase continuation. The local demo separates
two tasks: generating symbolic swaras with an existing variable-order n-gram
baseline, and selecting compatible existing vocal recordings. The initial
symbolic examples use Mohanam; the recording bank can filter exact supplied
raga and tala names. The main vocal showcase should stay with one raga/tala.

The symbolic model fits counts on the existing training split, excludes windows
with foreign-note errors, and generates eight positions after a sixteen-position
seed. The three practice inputs are hand-written demo seeds. Fixed random seeds
make outputs repeatable. They are not held-out evaluation examples.

The audio demo uses manually annotated swaras and timing. Prepared mode plays an
approved pair; retrieval mode selects a bank response from a different source
group. Retrieval matches raga/tala/meter and bounds tonic, tempo, and join phase,
then ranks coarse pitch contours and phrase duration. It neither clones Ishita's
voice nor makes an existing recording sing newly generated notes.

## Data provenance and counts

| Material | Current status | What can be claimed |
| --- | --- | --- |
| Existing symbolic corpus | 20 short composition fragments; provenance not independently verified | Engineering/research prototype input; not verified gold notation |
| Valid demo training subset | 449 overlapping T2 windows from 15 contributing training compositions | Count used by the current demo; windows are not independent performances |
| Three practice seeds | Hand-written input examples in `src/swaraga/demo.py` | Repeatable demonstration inputs |
| Ishita's recorded source takes | 0 received as of this checkpoint | Awaiting recordings; no vocal performance evaluation yet |
| Approved recorded pairs | 0 | Empty-bank handling is implemented |
| Test audio | Generated reference tones in temporary test folders | Plumbing checks only; not vocal data |

Update these counts with `python scripts/check_demo.py` after adding recordings.
List the number of **unique seeds**, **response options**, **original takes**, and
**source groups** separately. Do not equate multiple crops with independent data.
Owning a performance recording does not establish provenance of the old notation;
record sources and attribution for each performed composition separately.

## Existing results: presentation boundary

The saved baseline report uses T2 windows from 20 composition fragments; the test
table covers 50 overlapping windows. Its B1 contour distance is 1.11 versus 1.39
for the GRU and 1.40 for the Transformer. Those are **previous saved experiments**,
not a new result from this audio demo or a general claim about model superiority.
Their notation provenance and small, overlapping dataset limit interpretation.

Do not quote the legacy transition-legality values: the current implementation
counts context transitions and uses a more permissive direction check than the
decoder. Do not use the superseded constraint-ablation table. These claims are
omitted from the new app; no experiments were retrained for the audio prototype.

## Demo explanation / rehearsal script

1. Introduce the problem: given a short musical seed, explore what can follow.
2. Open Generated swaras. Show the sixteen-position input and eight-position
   output. Play and download the complete synthesized phrase. Explain that
   pitches are reference tones with fixed duration and no gamakas.
3. After recordings arrive, open Recorded vocal response. In Prepared mode,
   explicitly call it an approved pair sung by Ishita.
4. In Retrieval mode, show the selected candidate from another seed family.
   Explain that it is a retrieved recording, with manually annotated notes.
5. State limitations: tiny corpus, unverified old notation, manual annotations,
   no arbitrary audio transcription, no voice cloning, no learned vocal gamakas,
   and no completed independent listening evaluation.

Before audio arrives, step 3 demonstrates the honest empty state. Replace it
with three verified voice examples before recording the final backup video.

## Team listening sheet (fill tomorrow)

Use 1 (poor) to 5 (strong). Team ratings are a smoke check, not independent
expert validation. Save negative comments too.

| Query / response IDs | Mode | Listener | Continuity 1–5 | Audible artifacts 1–5 (5 = none) | Musical plausibility 1–5 | Notes / action |
| --- | --- | --- | --- | --- | --- | --- |
| Pending recordings | | | | | | |

## Contributions (update after review)

| Contributor | Assigned / implemented work | Verified status |
| --- | --- | --- |
| Ishita | Musical selection, own-voice recordings, swara/timing review, final musical approval | Awaiting handoff |
| Friend 1 — name pending | Demo captions and dictionary lookup | Assigned; not yet completed |
| Friend 2 — name pending | Catalog filter and approved recording metadata | Assigned; not yet completed |
| Codex assistance | Local app, symbolic adapter, audio preparation, validation/retrieval, tests, documentation, packaging | Implemented; see pre-recording verification report |

Use the actual contributors and the course's required AI-assistance disclosure.
Do not credit assigned tasks as completed work until they are returned and reviewed.
