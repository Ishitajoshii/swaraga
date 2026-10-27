# Swaraga: submission checklist

**Current checkpoint, 27 October:** four original recordings are integrated as
six prepared examples. Ishita approved their cuts/joins, the variable-tempo
beat maps for 30 and 31, and both retrieval combinations (30 to 31 and 31 to 30).
There are two timed retrieval candidates, one alternative each; no held-out
audio evaluation has been completed. Nyonika's contribution is merged in PR #2;
the other friend's assigned contribution is still pending. Final slides/report,
backup demo video, and submission remain
outstanding. The dated plan below
is retained as the original work queue; current counts and listening results
are in `docs/SUBMISSION_NOTES.md`.

Plan written for **today, 25 October 2026**, **tomorrow, 26 October**, and
**submission on 27 October**. If the submission time is early, treat tomorrow
evening as the absolute deadline. Times below are work blocks, not promises.

## Quick schedule to share with the team

The detailed checklists below are the work queue. Checked items now have working
code or documentation; unchecked items still need recordings, team input, or
final verification. The pre-recording local app and audio pipeline are implemented.

### Completed before recordings arrived (25 October)

- Local demo: `python scripts/run_demo.py`, then http://127.0.0.1:8765.
- Three deterministic symbolic examples with synthesized playback and WAV export.
- Empty vocal-bank state; prepared-pair and retrieval modes ready for real audio.
- PCM WAV trimming, catalog validation, manual timing, source-group isolation,
  matching, annotation display, and tala-position indicator implemented.
- Friend-file integration with temporary defaults; both friends' TODOs remain open.
- Recording guide: `docs/RECORDINGS.md`. Report/rehearsal notes:
  `docs/SUBMISSION_NOTES.md`. Verification: `reports/pre_recording_verification.md`.
- Local packaging command and synthesized backup WAVs in `.demo-artifacts/`.

**Still needs checking:** browser appearance and controls (computer-use was
blocked), actual vocal audio/annotations and musical joins, M4A conversion
(FFmpeg is not installed), final presentation/video, and team rehearsal.

| When | Ishita | Technical owner | Friends | Finish line |
| --- | --- | --- | --- | --- |
| Today, 25 Oct: first block | Confirm submission requirements; choose raga/tala; record a short test | Review test audio if available; settle demo scope and manifest | Receive their individual files | Recording recipe and responsibilities agreed |
| Today: main block | Record the priority seed/response takes | Build local app shell, symbolic adapter, and audio/retrieval plumbing | Finish the small TODO in their own file | App shell and both returned files ready for review |
| Today: final block | Back up takes and write filenames/swara notes | Check launch instructions and empty-bank behaviour | Explain their function in one sentence | Ready to accept real audio tomorrow |
| Tomorrow, 26 Oct: morning | Send the first 6 paired takes plus calibration and notes as soon as ready | Inspect, trim copies, annotate, and connect 3 showcase examples | Friend 2 enters approved metadata; Friend 1 reviews UI wording | First complete audible example |
| Tomorrow: afternoon | Listen and approve the 3 examples; redo only weak takes | Complete playback, verify labels/notes, fix major problems, freeze features | Both try the demo and report confusing steps | Three reliable examples |
| Tomorrow: evening | Rehearse musical explanation | Package code/audio, verify startup, save demo video and backup | Help with slides and rehearsal | Submission-ready package before bed |
| Submission day, 27 Oct | Final playback check and submission | Fix only blocking issues | Have their short explanations ready | Submit and save confirmation |

**Your minimum handoff:** one calibration take, 6 seed/response paired takes,
and the notes described below. Send that first; extras can follow. If you prefer
recording full songs, those are usable source recordings too: identify at least
three short seed/response sections with timestamps so integration can start.
There is no need to finish every song before handing over the first batch.

**Current handoff:** the pre-recording implementation is ready for the next
working session. Recording-dependent tasks below remain pending; they do not
run automatically while you record.

## The demo we are committing to

**Choose a short recorded seed in Ishita's voice, hear a compatible recorded
response in the same voice, and see the associated swaras and tala position.**

Start with **one raga and one tala**. Mohanam and Adi are the proposed defaults;
use a different raga if Ishita can sing and annotate it more confidently.
Keep one comfortable tonic and one tempo for the first recording session.

The vocal mode is **retrieval-assisted continuation**: it selects from recorded
phrases. It does not clone a voice or synthesize any arbitrary requested melody.
Show the existing n-gram model separately as **generated swaras**, with simple
instrumental playback if time permits. Do not imply a retrieved vocal recording
is singing those generated notes unless the notes actually match.

**Success on submission day:** a local app launches reliably; three prepared
examples work; the audience can hear the input and response; the explanation
accurately distinguishes recorded retrieval from symbolic generation.

## Who owns what

| Owner | Task | Expected effort |
| --- | --- | --- |
| Ishita | Choose repertoire, record, identify swaras and phrase boundaries, approve listening quality | Main musical work today/tomorrow |
| Main technical owner / Codex when working on the repo | App, audio processing, retrieval, integration, verification, packaging | Main engineering work |
| Friend 1 | Complete `team_tasks/demo_copy.py`; review the wording in the app | About 30–45 minutes, then a short review |
| Friend 2 | Complete `team_tasks/recording_catalog.py`; enter metadata for 3–5 approved recordings tomorrow | About 30–60 minutes plus metadata entry |
| All three | Listen to the final examples, rehearse, verify credits | Tomorrow evening |

These are genuine small contributions. Each friend should understand and be
able to explain their own function. Record their actual contribution in the
submission; follow the course's rules on AI assistance.

## Today: Ishita's recording preparation

- [ ] Confirm the submission time, required report format, demo duration, and
  whether the evaluator will have internet. Give these to the technical owner.
- [ ] Pick the one raga, tala, comfortable tonic, and tempo for the main demo.
  Keep the same settings throughout the initial collection.
- [ ] If possible, send **one 20–40 second test recording today**, before doing
  the rest. A quick check can catch clipping, loud background music, or unclear
  phrase boundaries. The rest can arrive tomorrow.
- [ ] Record in a quiet room, using the same device and roughly the same mic
  distance. Avoid clipping, reverb effects, noise gates, and background music.
- [ ] Use a metronome through earphones if useful; avoid an audible click or
  loud drone in the vocal recording. Count in silently or in a separate lead-in.
- [ ] Keep the original recording. Prefer WAV if readily available; phone M4A
  is acceptable. Do not delay recording to install conversion software, and do
  not convert a compressed file to WAV expecting better quality.
- [ ] Prioritise **sung swaras** for the first demo. Lyrics add pronunciation and
  text-alignment work. A lyrical excerpt can be an optional showcase later.

### What to record, in priority order

Do not spend the whole day recording all 20 songs. A coherent small phrase bank
in one raga is more useful for this deadline.

1. **Calibration:** 5–10 seconds of comfortable sustained Sa, then a slow ascent
   and descent, using the same tonic as the phrases. Note the tonic if known;
   otherwise mark it unknown so it can be checked. Do not guess its frequency.
2. **Minimum usable package:** 3 distinct seeds, each followed by 2 musically
   compatible responses. Sing each seed-response pair continuously, with a
   clear intended cut between them. This means **6 paired takes**.
3. **Preferred package:** 6 seeds with 2 responses each, or **12 paired takes**.
   Aim for a seed of about 1–2 tala cycles and a response of about 1 cycle;
   musical phrasing takes priority over an exact number of seconds.
4. **Extra evaluation material:** 2 additional seed phrases that will not enter
   the searchable phrase bank. These are for trying unfamiliar contexts, not
   for promising generalisation from such a small collection.
5. **Only after that:** one or two short song excerpts for presentation, or a
   second raga. Full songs are optional, not a prerequisite for the demo.

Sing natural gamakas you know confidently. Preserve the continuous performance;
do not record every note separately. At a phrase boundary, a short natural pause
is easier to join than cutting through an ornament or a sustained vowel.

### Recording handoff

- [ ] Put originals in a folder named `recordings_originals`.
- [ ] Use names such as `mohanam_seed01_optionA_take01.m4a` and
  `mohanam_seed01_optionB_take01.m4a`. Both contain a seed AND its response.
- [ ] Include a plain text note for each take, or one shared notes file, with:

```text
filename: mohanam_seed01_optionA_take01.m4a
raga: Mohanam
tala: Adi
tonic: [your actual setting, or unknown]
tempo: [actual metronome setting, or unknown]
tempo unit: [what each metronome click represents]
seed ends: [approximate timestamp]
response ends: [approximate timestamp]
seed swaras: [what you actually sang, including octave where known]
response swaras: [what you actually sang]
timing: [held notes, silence, cycle boundaries, pickup/eduppu if any]
notes: [retake needed, background noise, difficult ornament, etc.]
```

- [ ] If precise swara timings are difficult, provide the sequence and mark the
  phrase boundary. We can annotate the **three showcase examples** together.
  Do not invent note timings or quantize away the gamakas.
- [ ] Mark deliberate holds separately from silence. The current repo conflates
  these, and the audio demo must not inherit that ambiguity.
- [ ] Retain rejected takes, but label them. Identify your preferred take.

## Today: technical work that does not need the recordings

Do these in order. The two friend tasks must not block the core app.

- [x] Freeze the scope above; use the existing n-gram as the symbolic baseline.
  Avoid new neural training, voice cloning, arbitrary audio recognition, and
  broad dataset acquisition before submission.
- [x] Build a minimal local app: seed selection, raga/tala display, input audio,
  response selection, output audio, swara display, and clear mode labels.
- [x] Make the app handle an empty recording bank gracefully. It should explain
  that recordings have not been added yet, rather than crash or show fake data.
- [x] Define the manifest contract used by the app and Friend 2's file: clip ID,
  title, raga, tala, seed path, response path, split, and source-take identity.
  Keep precise timing annotations in a separate technical layer.
- [x] Implement and exercise the symbolic continuation adapter using existing
  examples. If adding instrumental playback, state that it is synthesized.
- [x] Implement PCM WAV loading, consistent playback format, trimming, and
  conservative level handling. Preserve the original files. Synthetic fixtures
  verify the pipeline; real-recording listening remains pending.
- [ ] If recordings arrive as M4A/MP3, install/locate FFmpeg and verify conversion.
  The optional conversion adapter is implemented but not exercised here.
- [x] Prepare a retrieval pipeline restricted to the selected raga and tala.
  Rank approved responses using annotated seed contours and compatible timing;
  keep pitch/tempo adjustments small or omit them entirely for this deadline.
- [x] Add an explicit prepared-example mode. If it uses an approved seed/response
  pairing, label it as such; do not present the pairing as an unseen prediction.
- [x] Make selectable examples deterministic, so rehearsals and demos agree.
- [x] Prepare the duration-aware event schema and validator: swara, octave,
  onset, duration, hold/rest distinction, and cycle position. Real annotations
  will be entered after recordings arrive; none are fabricated.
- [x] Separate recorded-vocal results from generated symbolic results in both
  the UI and the internal data flow.
- [x] Review the existing transition metric before quoting it. It currently
  counts input transitions and uses a more permissive direction check than
  decoding. The new demo omits that claim; old reports have not been regenerated.
- [x] Do not quote the superseded constraint-ablation table. Present saved
  experiments only with their dataset size and limitations attached.
- [x] Prepare an app launch command and a short README section. Torch is now
  optional in both instructions and installation configuration; the demo does
  not import it. NumPy is explicitly declared.
- [x] Run relevant checks on the new app and adapters; use a short smoke check
  for interface/config changes rather than retraining every model.
- [ ] Visually verify the browser layout, dropdowns, audio controls and download.
  API/HTTP checks passed; Windows computer-use stopped because it could not
  determine Edge's current URL confidently. Do not treat this as visually tested.

**Pre-recording checkpoint:** the local server and symbolic generation work,
the recording-bank interface is ready, and Ishita has a recording recipe.
The real catalog is empty. No placeholder vocal audio is presented as real.

## Today: the two friend tasks

Send each friend only their assigned `.py` file; all instructions and the
copyable ChatGPT prompt are inside it. They do not need the dataset or full repo.
If Python is unavailable, they can return the edited file and have the technical
owner run its check. Python 3.10 or newer is sufficient; no packages are needed.

Suggested message to Friend 1:

> Please finish the TODOs in demo_copy.py: three short app captions and one tiny
> dictionary-lookup function. The file explains everything and includes a
> ChatGPT prompt. Send back this file today, plus one sentence explaining what
> your function does. Tomorrow, help check the wording on the demo screen.

Suggested message to Friend 2:

> Please finish the TODO in recording_catalog.py: a small loop that filters a
> list of recordings. The file includes instructions and a ChatGPT prompt.
> Send back this file today, plus one sentence explaining the filter. Tomorrow
> I'll send the exact metadata for a few recordings for you to enter.

- [ ] Friend 1 receives only `team_tasks/demo_copy.py`. Complete its marked
  function and replace the requested placeholder text. Run the file to check it.
- [ ] Friend 2 receives only `team_tasks/recording_catalog.py`. Complete the small
  filtering function and run the file. Real recording entries can wait until
  tomorrow; the check uses invented metadata and does not require audio files.
- [ ] Each friend returns only their assigned file, or makes a commit containing
  only that file. No package installation or edits elsewhere are needed.
- [ ] Technical owner reviews each diff and integrates it. If Git is unfamiliar,
  accepting the edited file and making the merge together is sufficient.
- [ ] Run `python team_tasks/demo_copy.py` and
  `python team_tasks/recording_catalog.py` after receiving the completed files.
  Both should print a success message. Before completion, a TODO assertion or
  `NotImplementedError` is expected; it is not an installation problem.
- [ ] If using pull requests, each friend edits only their assigned file and
  opens a separate PR. Review and merge them independently; they do not overlap.
  Add their name and actual contribution to the final credits after review.

## Tomorrow morning: recordings and first audible result

- [ ] Ishita delivers the minimum package first; do not wait for every optional
  recording to be finished. Keep recording extras while integration starts.
- [ ] Listen to all submitted takes. Check clipping, audible clicks, consistent
  tonic/tempo, correct raga, and whether the response joins naturally.
- [ ] Select 3 strong showcase seeds and their approved responses first.
- [ ] Trim copies into seed/response files and annotate their swaras and timing.
  Keep source filenames and cut timestamps for traceability.
- [ ] Put working copies under `data/audio/`; agree on redistribution/storage
  before adding large audio files to Git. Keep originals backed up separately.
- [ ] Friend 2 enters 3–5 approved catalog records using the actual paths and
  metadata supplied by the technical owner. Do not guess musical metadata.
- [ ] Preserve source-take grouping when splitting data. Multiple crops or takes
  of the same seed/composition must not masquerade as independent held-out data.
- [ ] Connect the real files to the app and produce the first complete audible
  seed-to-response example before starting any optional feature.

## Tomorrow afternoon: improve the demo, then freeze it

- [ ] Add the remaining approved clips and verify retrieval excludes evaluation
  clips. Make response selection and mode labels visible.
- [ ] Listen to joins. Prefer phrase-boundary cuts; only crossfade where it does
  not blur an attack, erase a swara, or change the perceived rhythm.
- [ ] Confirm displayed notes describe the audio actually played. If exact
  highlighting is unavailable, show a phrase-level transcription and label it.
- [x] Implement a simple tala-cycle indicator for manually annotated, metered
  recordings. It uses the supplied beat phase and tempo, not output note count.
- [ ] Verify the indicator visually and against Ishita's actual performances.
- [x] Implement complete-phrase WAV download/export for both demo modes.
- [ ] Preserve and listen to the exported vocal WAV for each showcase example.
- [ ] Try two held-out seed contexts; report what happened without overstating
  success. A tiny curated demo is not evidence of arbitrary-input capability.
- [ ] Ishita and friends rate continuity, audible artifacts, and overall musical
  plausibility for the showcase clips. Record comments, including failures.
  Team listening is a smoke check, not independent expert validation.
- [ ] Fix the largest audible/UI problems. Freeze features by late afternoon.

### Cut rules if time gets tight

- No usable audio by tomorrow midday: finish the symbolic/instrumental demo and
  include the voice examples only if they can be verified in time.
- Retrieval joins still sound poor: use openly labelled prepared examples and
  show symbolic generation separately. Do not disguise preselected audio as AI
  generation or as a retrieval result.
- Drop live recording, arbitrary uploads, automatic raga/tala detection, a second
  raga, lyric alignment, and voice conversion before compromising the core demo.
- Do not train a larger model overnight. Spend that time listening and packaging.

## Tomorrow evening: submission package

- [x] Test the app startup command from a fresh terminal on this machine.
  Recheck after integrating real recordings and on any different demo machine.
- [ ] Verify all showcase files are included and paths are relative to the repo.
- [ ] Test the intended machine with internet disconnected if an offline demo
  is required. Confirm no unexpected model download is needed on first use.
- [x] Run pre-recording automated tests and an HTTP/audio smoke test.
- [ ] Repeat the complete browser/audio smoke test with the final recordings.
- [ ] Record a 60–90 second backup demo video with audible sound.
- [x] Prepare report/rehearsal notes covering problem, scope, architecture,
  baseline evidence, limitations and contributions in `docs/SUBMISSION_NOTES.md`.
- [ ] Turn the notes into the final presentation and add verified recording
  counts, listening results and actual team contributions.
- [x] Document dataset provenance honestly: separate the existing 20 symbolic
  fragments from Ishita's forthcoming recordings. The notes explicitly call
  the old provenance unverified; checking original notation sources is pending.
- [ ] List exact numbers of recorded seeds, response options, and source takes.
- [ ] Add a contribution table with each teammate's actual work.
- [x] Prepare a local snapshot tool and synthesized reference-WAV backups;
  create a ZIP snapshot and verify its checker after extraction to a separate
  folder. This uses the current Python environment, not a clean-machine install.
- [ ] Save the final recording-integrated snapshot and separately back up
  original recordings, vocal exports, and the demo video.
- [ ] Rehearse once with all three people, using the submission machine.

## Submission morning, 27 October

- [ ] Open the frozen version and play all three examples once.
- [ ] Confirm the slide deck/report, code, audio assets, and backup video are in
  the required submission location.
- [ ] Make no new model or dependency changes unless something is broken.
- [ ] Submit before the actual deadline and keep the receipt/confirmation.

## Definition of done

- [x] One command launches the demo.
- [ ] Three verified examples play from start to finish.
- [ ] Vocal playback uses Ishita's actual recordings and matching annotations.
- [x] Recorded retrieval and newly generated swaras are clearly distinguished
  in the code and UI labels; final browser review remains above.
- [ ] The presentation makes no claim of arbitrary-song transcription, voice
  cloning, learned gamaka synthesis, or general Carnatic mastery.
- [ ] Both friends' small contributions are integrated and understood.
- [ ] A working offline backup exists.

Checked items record implemented and verified pre-recording work, with limits
noted above. As of 27 October, Nyonika's contribution in
[PR #2](https://github.com/Ishitajoshii/swaraga/pull/2) has been reviewed and
merged. Although her PR changed both helper files, it completes only her
contribution. The other friend's assigned contribution is still pending.
Earlier friend-task assignments above are retained as the original work queue.
