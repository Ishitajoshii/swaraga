# Pre-recording implementation verification

Date: 25 October 2026. No real vocal recordings had been supplied.

## Implemented

- Local Python HTTP app serving bundled HTML, CSS, and JavaScript on loopback.
- Three fixed-seed symbolic examples using the existing B1 n-gram and constrained
  decoder, without importing torch or downloading models.
- Input/output/combined synthesized PCM WAV playback endpoints and export.
- Empty vocal-bank state, separately labelled prepared and retrieved responses.
- Catalog/annotation contract, corruption/path checks, source-group split checks,
  deterministic ranking, timing validation, and annotated tala-position UI.
- Original-preserving audio trimming with cut provenance and attenuation-only
  level handling. PCM WAV decode/resample/encode is exercised.
- Automatic use of each friend's completed module after its own checks pass;
  temporary defaults let the app run while their two TODOs remain unfinished.
- Setup/recording instructions, submission notes, synthesized backup WAVs,
  and a local snapshot packaging command.

## Executed checks

| Check | Result |
| --- | --- |
| `python -m pytest -q -p no:cacheprovider` | **260 passed** |
| `python -m pytest tests/test_demo.py -q -p no:cacheprovider` | **14 passed**, also re-run after the Windows port-binding fix |
| `node --check demo/app.js` | Passed |
| `git diff --check` | Passed; Git noted normal LF/CRLF conversion |
| `python scripts/check_demo.py` | 3 symbolic examples, 0 recorded pairs, no warnings |
| Fresh `python scripts/run_demo.py --port 8765` startup | Local HTTP server starts successfully |
| HTTP root, state, audio, invalid requests and traversal checks | Passed |
| Synthesized backup exports | Three WAVs, each mono 24 kHz, 16-bit, 7.68 seconds |
| ZIP snapshot extracted into a separate local folder | CRC check passed; packaged checker produced 3 symbolic examples with no warnings |

The test suite covers original preservation, overwrite rejection, stereo PCM
conversion, no quiet-audio boosting, annotation holds/rests, invalid timing,
corrupt files, evaluation exclusion, group leakage, musical-setting/tempo/phase
filters, deterministic ordering, friend-module integration, and combined export.
Vocal paths were exercised with temporary synthesized fixtures, not fake voices.
The server also rejects a second instance on its port, avoiding stale previews
from two Windows processes binding the same address.

The demo trains on **449 valid overlapping windows from 15 contributing training
compositions**, excluding windows containing foreign-note errors. These are not
449 independent musical examples. There are still 20 fragments in the underlying
symbolic corpus. Existing experiment reports were not retrained or overwritten
to claim new model performance.

## Explicitly not verified yet

- Browser layout, control interactions, actual browser playback and download.
  Windows computer-use stopped because it could not determine Edge's current
  URL confidently. No subsequent UI automation was attempted.
- Actual singing quality, joins, timing annotations, raga fidelity, or listening
  ratings. These require Ishita's recordings and approval.
- M4A/MP3 conversion: the optional FFmpeg adapter exists, but FFmpeg is not on
  PATH here. PCM WAV is the verified path.
- Physical internet-disconnected rehearsal, clean-machine dependency install,
  final slides/video, completed friend contributions, and final submission.

The frontend has no external fonts/scripts/services, and the server uses only
local assets and model counts. This supports offline operation after installation;
it is not a claim that a physical disconnected-machine rehearsal was performed.

## Metrics decision

The current legacy `transition_legality` metric includes context transitions and
uses a direction-permissive check. The new app does not present that number or
the superseded ablation table. Correcting and re-running historical experiments
is deferred; the limitation is documented in the README and submission notes.
