# Swaraga

**A Carnatic music companion for exploring melodic continuations.**

Swaraga turns a short swara phrase into a playable musical idea. Explore
raga-conditioned note generation, listen to recorded call-and-response phrases,
and follow reviewed swara and tala annotations in a local browser app.

Built with Python, NumPy, pandas, PyArrow, and vanilla JavaScript. The core app
runs on CPU, works offline after setup, and requires no account or API key.

## Features

- **Generate swaras:** three Mohanam practice presets, each with a 16-note
  opening and an eight-note continuation. A variable-order n-gram model and
  constrained decoder combine the training corpus with 63 source-attributed
  notation passages from two Mohanam compositions.
- **Listen and export:** play the opening, continuation, or complete phrase,
  then download a WAV. Generated phrases use articulated instrumental reference
  tones with uniform timing.
- **Explore recorded responses:** play curated vocal pairs or retrieve a
  compatible response from another source group. Matching considers raga,
  tala, tonic, tempo, phrase contour, and join phase.
- **Follow the music:** reviewed note-level recordings support swara and tala
  highlighting, including beat maps for variable tempo. Phrase-only recordings
  display supplied notation without inferred timing.
- **Experiment from the terminal:** enter your own swaras, select a raga,
  and reproduce preprocessing, baseline, and optional neural experiments.

## Run locally

Requirements: **Python 3.10+** and Git. FFmpeg is only needed to import MP3/M4A
recordings or rebuild the optional Hindolam audio assets. PyTorch is optional.

```bash
git clone https://github.com/Ishitajoshii/swaraga.git
cd swaraga
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux (use python3 above if python is unavailable)
source .venv/bin/activate
```

Install dependencies and start the app from the repository root:

```bash
python -m pip install -r requirements.txt
python scripts/run_demo.py
```

Open **http://127.0.0.1:8765**, select **Generated swaras**, choose a preset,
and play the complete phrase. Stop with `Ctrl+C`. If the port is busy, run
`python scripts/run_demo.py --port 8766` and open that port instead.

If PowerShell blocks activation, use `.\.venv\Scripts\python.exe` in place of
`python` for the install and run commands; changing execution policy is unnecessary.

### What works in a fresh clone?

The repository includes the symbolic dataset, processed splits, notation
supplement, and application source. **Generated playback and text continuation
work without private recordings or a model download.**

Vocal WAV/MP3/M4A files are excluded from Git. The checked-in catalog describes
six reviewed Mohanam pairs from four source recordings, but a fresh clone has
no playable vocal bank and reports missing-audio warnings. These warnings do
not prevent symbolic playback. Restore the matching audio files from an
authorized local snapshot, or add your own catalog entries and annotations
using the [recording guide](docs/RECORDINGS.md). Two of the reference pairs
have the timing annotations required for retrieval; the others support prepared
playback only.

## Continue your own phrase

```bash
python scripts/predict_text.py --list-ragas
python scripts/predict_text.py --raga Mohanam --input "S R G P D P G R" --notes 8 --seed 42
python scripts/predict_text.py
```

The last command starts an interactive prompt. Use spaces between notes,
`S'` for upper Sa, `S.` for lower Sa, and `:quit` to exit. Bare swaras resolve
against the selected raga; explicit variants such as `G3` are also accepted.
The CLI uses the original multi-raga B1 model. The browser additionally uses
the Mohanam notation prior and a repeated-note playback preference, so their
outputs need not match.

## Reproduce the pipeline

Run these commands from the repository root with the environment active:

```bash
python scripts/run_preprocessing.py --seed 42
python scripts/run_experiments.py --rung T2 --seed 42
python -m pytest -q -p no:cacheprovider
```

Preprocessing reads `train-00000-of-00001.parquet`, cleans and normalizes the
records, rebuilds swara/token sequences from notation, and splits by whole
composition. It writes datasets under `data/` and quality reports under
`reports/`. Supply `--source path/to/dataset.parquet` to use another corpus
with the same schema. Identical input and seed produce deterministic splits.

The experiment command writes `reports/baseline_results.json` and `.md`;
omit `--rung T2` to run all three horizons. T1 predicts four notes from 12,
T2 predicts eight from 16, and T3 uses four avartanas to predict two.
These commands overwrite generated data/reports; use a separate checkout to
compare runs. Dependency versions are minimum bounds rather than a lockfile,
so record `python --version` and `python -m pip freeze` when comparing results.

For the optional GRU and Transformer experiments:

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python scripts/run_experiments.py --seed 42
python scripts/run_scaling_study.py
```

The experiment runner includes neural models automatically when PyTorch is
installed; otherwise it runs the baselines. Neural tests skip without PyTorch.
The browser app does not train or import a neural model.

### Validate and package a complete audio installation

Once the catalog's recordings are available locally:

```bash
python scripts/check_demo.py
python scripts/package_demo.py
```

The checker validates playback paths and exports complete-phrase WAV backups
with hashes and runtime versions into `.demo-artifacts/`. It exits nonzero if
assets are missing, so it is not a clean-clone setup requirement. Packaging
runs that check first, then creates a ZIP containing source, public docs, data,
local audio, and playback backups. It excludes personal planning notes,
environments, Git metadata, and `recordings_originals/`. The ZIP includes local
audio even though Git ignores it; review the contents and recording permissions
before sharing. It is not an offline dependency installer.

## How it works

1. **Prepare notation:** normalize composer, raga, and tala metadata; resolve
   swara variants; retain rests and phrase structure; split by composition.
2. **Model continuation:** learn scale-degree sequences with a variable-order
   Markov model, then reweight browser predictions using the Mohanam notation prior.
3. **Constrain and render:** apply the supplied raga grammar at decoding time
   and synthesize reference tones for listening.
4. **Retrieve recordings:** validate annotations and source-group separation,
   filter compatible recorded responses, and rank pitch contours and duration.

| Path | Purpose |
| --- | --- |
| `demo/` | Browser interface and playback controls |
| `src/swaraga/` | Preprocessing, models, decoding, audio, and retrieval |
| `scripts/` | App launcher, importers, experiments, and packaging |
| `config/` | Raga grammar and normalization dictionaries |
| `data/knowledge/` | Source-attributed notation and provenance manifests |
| `data/processed/`, `data/splits/` | Model inputs and composition-level splits |
| `team_tasks/` | Caption and recording-catalog modules loaded by the app |
| `tests/` | Automated validation |
| `reports/` | Dataset statistics and historical experiment outputs |

## Scope and evidence

Swaraga currently focuses on short melodic phrases. Generated audio uses
reference pitches, not synthesized singing or reconstructed gamakas. Recorded
responses are existing performances, and only reviewed timing annotations
drive tala highlighting.

The legacy corpus has **20 compositions across 20 ragas** and unverified
provenance; it supports pipeline experiments, not claims of broad musical
quality. The 63 Mohanam passages come from two compositions and are training-only
material. The two timed reference recordings provide one alternative response
per query, not a large-bank retrieval benchmark.

Historical reports are retained for reproducibility. Their transition-legality
metric includes input transitions and differs from the decoder's direction-aware
check, so its ablation is not evidence of improved generated motion. Pitch
membership follows from the representation and does not establish raga identity
or musical quality. Source attribution does not imply redistribution rights;
the notation guides document the available provenance and reuse limits.

## Technical guides

- [Add and validate recordings](docs/RECORDINGS.md)
- [Mohanam notation sources and reproduction](docs/MOHANAM_KNOWLEDGE.md)
- [Hindolam extension and source review](docs/HINDOLAM_REVIEW.md)
- [Dataset statistics](reports/dataset_report.md)
- [Data-quality findings](reports/data_quality_log.md)
