# Submission working notes

Status: recording-integrated demo, 27 October 2026. Six prepared vocal pairs
are available; takes 30 and 31 have reviewed beat maps and can retrieve each
other's responses. Ishita approved all prepared pairs, both timing reviews,
and both retrieved combinations. Nyonika's captions, dictionary lookup, and
catalog filter are merged in PR #2. This completes Nyonika's contribution only;
the other friend's assigned contribution and final presentation/video remain
outstanding.

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

The audio demo uses supplied swaras and reviewed annotations. Prepared mode plays an
approved pair; retrieval mode selects a bank response from a different source
group. Retrieval matches raga/tala/meter and bounds tonic, tempo, and join phase,
then ranks coarse pitch contours and phrase duration. It neither clones Ishita's
voice nor makes an existing recording sing newly generated notes.

The timing in takes 30 and 31 follows Ishita's self-counted tala using
signal-derived attack markers that she reviewed with click overlays. The
beat maps allow her pace to change. The other four pairs show phrase notation
without note highlighting or a tala clock. With only two timed exercises,
retrieval has one eligible alternative per query; this does not demonstrate
ranking quality across many candidates or performance on unfamiliar inputs.

## Data provenance and counts

| Material | Current status | What can be claimed |
| --- | --- | --- |
| Existing symbolic corpus | 20 short composition fragments; provenance not independently verified | Engineering/research prototype input; not verified gold notation |
| Valid demo training subset | 449 overlapping T2 windows from 15 contributing training compositions | Count used by the current demo; windows are not independent performances |
| Three practice seeds | Hand-written input examples in `src/swaraga/demo.py` | Repeatable demonstration inputs |
| Ishita's recorded source takes | 4: recordings 29-32 | Her own performances in Mohanam, Adi tala, G# / 5.5 shruti |
| Approved recorded pairs | 6 seed clips and 6 paired response clips | Three overlapping Ninnu Kori pairs from take 29, plus three practice exercises |
| Timed retrieval candidates | 2: recordings 30 and 31 | Reviewed coarse swara/beat maps; one alternative response per query |
| Retrieved combinations checked | 2: 30 to 31 and 31 to 30 | Ishita judged both good; qualitative team listening only |
| Test audio | Generated reference tones in temporary test folders | Plumbing checks only; not vocal data |

Recheck these counts with `python scripts/check_demo.py` after adding recordings.
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
3. Open Recorded vocal response. In Prepared mode,
   explicitly call it an approved pair sung by Ishita.
4. In Retrieval mode, show the selected candidate from another seed family.
   Choose recording 30 or 31. Explain that it is a retrieved recording, with
   supplied notes and a reviewed beat map that follows the singer's pace.
5. State limitations: tiny corpus, unverified old notation, manual annotations,
   no arbitrary audio transcription, no voice cloning, no learned vocal gamakas,
   and no completed independent listening evaluation.

For a short demo, show one generated example, one prepared Ninnu Kori pair,
and one retrieval combination. Save a 60-90 second backup video with sound.

## Team listening record

Use 1 (poor) to 5 (strong). Team ratings are a smoke check, not independent
expert validation. Save negative comments too.

| Query / response IDs | Mode | Listener | Continuity 1–5 | Audible artifacts 1–5 (5 = none) | Musical plausibility 1–5 | Notes / action |
| --- | --- | --- | --- | --- | --- | --- |
| All six prepared pairs | Prepared | Ishita | Not scored | Not scored | Not scored | Confirmed cuts and joins are good |
| mohanam_take30 / mohanam_take31 | Retrieval | Ishita | Not scored | Not scored | Not scored | Confirmed the retrieved combination is good |
| mohanam_take31 / mohanam_take30 | Retrieval | Ishita | Not scored | Not scored | Not scored | Confirmed the retrieved combination is good |

No numeric ratings were requested or inferred. Timing review for both practice
takes was separately approved. These checks are not an independent evaluation.

## Contributions

| Contributor | Assigned / implemented work | Verified status |
| --- | --- | --- |
| Ishita | Musical selection, own-voice recordings, swara/timing review, musical approval | Completed for the six prepared pairs and two retrieved combinations |
| Nyonika (`Nyonikaa`) | Demo captions, dictionary lookup with fallback, and bank-only recording filter with optional exact raga matching | Reviewed and merged in [PR #2](https://github.com/Ishitajoshii/swaraga/pull/2); existing recording metadata preserved |
| Other friend — name pending | Separate assigned contribution | Still pending; not completed by Nyonika's PR |
| Codex assistance | Local app, symbolic adapter, audio preparation, validation/retrieval, tests, documentation, packaging | Implemented; see pre-recording verification report |

Use the actual contributors and the course's required AI-assistance disclosure.
Do not credit assigned tasks as completed work until they are returned and reviewed.
