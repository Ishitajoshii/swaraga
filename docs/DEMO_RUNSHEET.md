# Mohanam demo run sheet

Frozen scope: 28 October 2026. No new recordings are needed.

## Start

From the extracted project folder or the existing repository:

```powershell
python scripts/run_demo.py
```

Open <http://127.0.0.1:8765/>. Leave the terminal running. If the port is occupied,
use the already-running demo, or launch with `--port 8766` and open that port.
Python and the existing dependencies must be installed; this is not a standalone
application installer. Runtime versions are recorded in `backup_audio/check.json`
inside the snapshot.

## A 90-second presentation

1. **Explain:** “Swaraga explores short Carnatic phrase continuation in Mohanam.
   It generates symbolic notes and separately retrieves existing sung responses.”
2. **Generated swaras:** choose ascending practice. Play the complete phrase.
   Explain the sixteen-note opening and eight generated notes. The instrumental
   sound uses distinct attacks, with a preference against long repeated runs.
   Timing is uniform and the sound does not reproduce vocal gamakas.
3. **Recorded vocal response / Prepared example:** choose the first Ninnu Kori
   pair. Play the complete phrase. This is Ishita's reviewed continuous singing,
   split into an opening and its original continuation.
4. **Retrieve from another seed family:** choose take 30. The response comes
   from take 31. Play the complete phrase; optionally show either half separately
   to display its reviewed note and tala highlighting. Beat maps follow the
   singer's changing pace. The complete-phrase player does not show that highlighting.
5. **Conclude:** “This is a small, reviewed demonstration. There are two timed
   exercises, giving one alternative per retrieval query. It does not synthesize
   new singing or establish general performance across ragas.”

No Hindolam vocals belong in this presentation: the archive excerpts contained
lyrics and were rejected. Their stored files are audit history only. The
separate Hindolam instrumental page is exploratory and optional, not completed
multi-raga validation.

## If the app fails during presentation

Play the corresponding files from `backup_audio/` in the extracted snapshot:

| Demonstration | File |
| --- | --- |
| Generated ascending example | `symbolic-prepared-ascent.wav` |
| Prepared Ninnu Kori pair | `vocal-prepared-ninnu_kori_pair01.wav` |
| Take 30 with take 31's response | `vocal-retrieval-mohanam_take30-to-mohanam_take31.wav` |

All eleven complete phrases are included. WAV playback needs no Python or
network. To refresh these exports in the working repository, run
`python scripts/check_demo.py`; they appear in `.demo-artifacts/audio-backups/`.
To create a new complete snapshot, run `python scripts/package_demo.py`.

## Final check on the presentation machine

Open the app, play the three examples above, and try Download WAV once.
This is a device/speaker check, not another request to approve the music.
The automated checks cover all 33 audio paths, not the physical audio output.
Browser automation could not finish because the app-approval request timed out.

Keep the snapshot and any course-required slides/video together. A demo video,
final presentation and course submission are not created by the packaging tool.
