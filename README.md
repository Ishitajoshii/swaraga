# Swaraga - Carnatic composition dataset preprocessing

## Local submission demo

From the repository directory, install the light dependencies once and start:

```powershell
python -m pip install -r requirements.txt
python scripts/run_demo.py
```

Open **http://127.0.0.1:8765**. Use `--port 8766` if that port is occupied.
Stop the server with Ctrl+C. No account, model download, hosted API, or internet
connection is needed after dependencies are installed. Python 3.10+ is required.

- **Generated swaras:** three Mohanam practice seeds, existing B1 n-gram
  continuation, fixed random seeds 42/43/44, synthesized reference playback,
  and complete-phrase WAV downloads. Timing is uniform, not inferred tala timing.
  Ishita's instrumental-playback preference is applied in the demo: distinct
  decaying note attacks, and at most two consecutive identical generated pitches
  when a legal alternative exists. This is an optional decoder preference;
  historical experiment defaults and recorded performances retain their behavior.
- **Recorded vocal response:** six approved prepared pairs in Mohanam/Adi,
  G# / 5.5 shruti: three overlapping Ninnu Kori pairs from take 29, plus the
  three practice exercises in takes 30-32. Ishita approved their phrase cuts
  and joins. Takes 30 and 31 now also have reviewed note/beat markers, refined
  response boundaries and variable-tempo tala highlighting. Each can retrieve
  the other's response; with two eligible exercises there is only one alternative
  per query. Ninnu Kori and take 32 remain phrase-only and excluded from retrieval.
  There are four original source recordings. Vocal audio is existing material.
- **Friend tasks:** the two files under `team_tasks/` stay intentionally
  unfinished. Safe defaults keep the demo running. After a friend finishes and
  their file passes its checks, restarting the app picks up their contribution.

Recording manifest, trimming commands, timing schema, and review procedure:
[docs/RECORDINGS.md](docs/RECORDINGS.md). Schedule and remaining work:
[SUBMISSION_TODO.md](SUBMISSION_TODO.md).

```powershell
python scripts/check_demo.py       # validate; save three synthesized backup WAVs
python -m pytest -q -p no:cacheprovider
python scripts/package_demo.py     # create a local source/audio ZIP in .demo-artifacts/
```

The ZIP includes working audio and the original MP3s currently in `data/audio/`,
even though Git ignores audio files. It excludes `recordings_originals/`,
environments, and Git metadata. It is a local snapshot, not a complete
offline Python installer; keep the existing environment and separately back up
original recordings and the final demo video. The existing source parquet is
included for reproducing preprocessing; its provenance remains unverified.

The demo omits the legacy transition-legality and constraint-ablation claims.
The transition metric includes input transitions and does not use the decoder's
direction-aware mask; old values should not be used as evidence of generated
transition quality. Existing symbolic dataset provenance is still unverified.

Torch is **optional**, and is no longer installed by `requirements.txt`. Only
neural experiments need it; install separately if required. Nothing in the new
demo imports or trains a neural model.

## Existing preprocessing pipeline

Implementation of the pipeline specified in [`preprocessing.md`](preprocessing.md):
a clean, standardised, model-ready dataset for training a composition generator
conditioned on **composer**, **raga** and **tala**.

```
train-00000-of-00001.parquet
        v
data/raw/raw_dataset.parquet
        v   clean      - integrity: encoding, whitespace, duplicates, notation validity
data/interim/cleaned_dataset.parquet
        v   normalize  - controlled vocabularies + rebuilt musical representation
data/processed/normalized_dataset.parquet -> data/processed/trinity_dataset.parquet
        v   split      - 80/10/10 by whole composition
data/splits/{train,val,test}.jsonl
```

## Running it

```bash
pip install -r requirements.txt
python scripts/run_preprocessing.py
pytest                                  # 88 tests
```

The run is deterministic: the same input and seed give byte-identical splits.
Pass `--source` to ingest a different parquet and `--seed` to reshuffle.

## Layout

| Path | What it is |
| --- | --- |
| `src/swaraga/config.py` | paths, split ratios, thresholds, token vocabulary |
| `src/swaraga/melakarta.py` | the 72-melakarta system; resolves swara variants |
| `src/swaraga/notation.py` | notation parser and the two tokenisers |
| `src/swaraga/text_norm.py` | Unicode, dash/quote folding, whitespace |
| `src/swaraga/period.py` | `period` free text -> century and life years |
| `src/swaraga/normalizers/` | composer, raga and tala controlled vocabularies |
| `src/swaraga/clean.py` | stage 1 - integrity |
| `src/swaraga/normalize.py` | stage 2 - vocabulary and musical representation |
| `src/swaraga/validate.py` | statistics and report (PRD 6) |
| `src/swaraga/split.py` | train/val/test splitting (PRD 7) |
| `src/swaraga/quality_log.py` | structured data-quality log |
| `src/swaraga/pipeline.py` | orchestration |
| `config/*.json` | the three normalisation dictionaries |
| `reports/` | statistics + data-quality log |

## Key decision: the `tokens` column is rebuilt, not reused

The raw `tokens` column cannot be used as a training target:

- **Gamaka tags are noise.** Every single note in all 20 compositions carries
  `GMK_AHAT`. The real ornamentation sits in `gamaka_annotations_json`.
- **Swara variants contradict the raga.** Notes are written `_2` almost
  everywhere, so Todi's tokens claim R2/D2 when Todi has R1 and D1.
- **Every rest is missing.** The notation contains 111 karvai (rest) positions;
  the token column has none of them.

`sections_json` holds the human notation those tokens were derived from, so the
pipeline re-derives the sequence from it and resolves each variant from the
composition's melakarta number - which is deterministic and, for all 10
melakartas present, yields the musically correct scale (pinned in
`tests/test_melakarta.py`).

Letter case is **not** used to resolve variants: the corpus writes G2 as `G` in
one row and `g` in another, and uses `M` for both M1 and M2 in different rows.
Case and `+` markers are preserved verbatim in `Note.raw` for traceability.

## Two sequence representations

Both are emitted per composition; pick one at training time.

| Field | Shape | Octave | Structure |
| --- | --- | --- | --- |
| `swara_sequence` | `["S","R2","G3","[REST]","P","D2","S'"]` | inline `'` | flat |
| `token_sequence` | `["[BOS]","[TALA:Adi]","[SECTION:Pallavi]","[BAR]","S",...,"[EOS]"]` | `[OCTAVE_UP]` / `[OCTAVE_DOWN]` | bars, sections, tala |

`swara_sequence` matches the worked example in `preprocessing.md` section 5.
`token_sequence` exercises the remaining special tokens and keeps the metric
structure a generator needs.

## Current dataset

| Metric | Value |
| --- | ---: |
| Compositions | 20 |
| Unique composers | 8 |
| Trinity compositions | 8 |
| Unique ragas | 20 |
| Unique talas | 6 |
| Mean sequence length | 50.9 |
| Swara vocabulary | 24 |

Full numbers in [`reports/dataset_report.md`](reports/dataset_report.md); every
repair and flag in [`reports/data_quality_log.md`](reports/data_quality_log.md).

## Phase 2 - raga-conditioned continuation

The modelling project is specified in [`PRD.md`](PRD.md). Run the baselines:

```bash
python scripts/run_experiments.py          # all rungs
python scripts/run_experiments.py --rung T2
```

**Task ladder** (PRD section 3) - the horizon is staged so no rung is blocked
on data:

| Rung | Task | Windows | Role |
| --- | --- | ---: | --- |
| T1 | 12 notes -> next 4 | 718 | unit-test rung |
| T2 | 16 notes -> next 8 | 558 | **v1 target** |
| T3 | 4 avartanas -> next 2 | 59 | headline goal, data-gated |

**Current T2 results** (seed 42; `GT` is the human ground truth, scored as if
it were a model):

| Model | contour dist | exact | nyasa | novelty | ppl |
| --- | ---: | ---: | ---: | ---: | ---: |
| GT (human) | 0.00 | 1.00 | 0.50 | 0.13 | - |
| B0 random walk | 3.21 | 0.09 | 0.42 | 1.00 | - |
| B0.5 direction | 1.45 | 0.15 | 0.36 | 0.87 | - |
| **B1 n-gram** | **1.11** | **0.32** | **0.56** | 0.16 | 2.3 |
| B2 retrieval | 1.52 | 0.22 | 0.38 | 0.76 | - |

B1 clears the B0.5 bar, which is the v1 success criterion. Raga conformance,
transition legality and exact length are 1.00 for every model including the
random walk - they are guaranteed by the constrained decoder, so they verify
the system rather than ranking models.

### Three things that are easy to get wrong here

1. **Raga conformance is specified, not learned.** With one composition per
   raga it cannot be learned, but arohanam/avarohanam state it exactly, so
   `decode.py` masks illegal notes before sampling. Output is in-raga by
   construction - property-tested across every model, rung and seed.

2. **Novelty must be read against `GT`, never against 1.00.** Real human
   continuations here score 0.13, because the degree vocabulary is 15 symbols
   wide and the repertoire is formulaic. Heavy n-gram reuse is normal music.
   B1 at 0.16 is near-human; B0 at 1.00 is not creative, it is random.

3. **The models reason in scale degrees, not swaras.** Each swara maps to its
   index in its own raga's scale, so all 20 ragas pool into one training set
   and a contour learned in Mohanam can be emitted in Hindolam. The cost is
   that a degree model captures contour, not raga character.

### Known limits

- **Corpus provenance is unverified** and shows signs of being generated
  (uniform `sa_hz`, uniform gamaka tags, a rishabha in Hindolam). PRD section
  2.1 makes checking this a gating task before any result is reported.
- Every raga has one composition, so raga-specific character is unlearnable.
- T3 runs but is starved: 59 windows from 6 compositions, 33 from one piece.

## Phase 3 — the neural models (M1)

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
python scripts/run_experiments.py       # baselines + M1
python scripts/run_scaling_study.py     # scaling curve + constraint ablation
```

`torch` is **optional**: it is imported lazily, the B0–B2 baselines and the
whole preprocessing pipeline run without it, and the neural tests skip cleanly
when it is absent. CPU only — no GPU anywhere in this project.

Two conditional architectures, both tiny because the data is tiny:

| Model | Params | Notes |
| --- | ---: | --- |
| `M1-gru` | 90,208 | embedding 64 + raga 16 + tala 8 → GRU 128 |
| `M1-transformer` | 309,152 | d_model 128, 2 layers, 4 heads, causal |

### Results

**T1** (12 notes → next 4):

| Model | contour ↓ | exact | nyasa | novelty | ppl |
| --- | ---: | ---: | ---: | ---: | ---: |
| GT | 0.00 | 1.00 | 0.55 | 0.12 | - |
| B0.5 | 1.20 | 0.23 | 0.45 | 0.82 | - |
| B1 | 0.90 | 0.46 | 0.55 | 0.20 | 2.2 |
| **M1-gru** | 1.12 | 0.53 | 0.58 | 0.26 | 2.1 |
| M1-transformer | 1.14 | 0.50 | 0.52 | 0.29 | 3.1 |

**T2** (16 notes → next 8):

| Model | contour ↓ | exact | nyasa | novelty | ppl |
| --- | ---: | ---: | ---: | ---: | ---: |
| GT | 0.00 | 1.00 | 0.50 | 0.13 | - |
| B0.5 | 1.45 | 0.15 | 0.36 | 0.87 | - |
| **B1** | 1.11 | 0.32 | 0.56 | 0.16 | 2.3 |
| M1-gru | 1.39 | 0.26 | 0.50 | 0.38 | 2.4 |
| M1-transformer | 1.40 | 0.25 | 0.58 | 0.48 | 4.8 |

At the **short** horizon the GRU beats the n-gram on exact match and
perplexity; at the **longer** horizon the n-gram wins on every column. That
horizon effect is itself a finding — the neural models hold up for four notes
and degrade over eight, which is what you would expect from models with
~500 effective training examples.

### An important correction about "100% raga conformance"

Every model, including the untrained random walk, scores 1.00 raga conformance
— and it still does with the constraint mask **switched off**. That is not
evidence the system works. It is a property of the *representation*: degrees
map back to swaras modulo the raga's own scale, so an out-of-raga note is
literally unrepresentable.

What the decoder's mask actually buys is **legal motion** — a raga's ascending
and descending paths differ, and nothing in the degree encoding forces a model
to respect that. `reports/scaling_study.md` reports the ablation on transition
legality for this reason. Quoting raga conformance as a result would overstate
what the grammar contributes.

## Honest limits of the current data

These are logged as warnings by the pipeline, not silently smoothed over:

1. **20 compositions is far too few** to train a composer-conditioned
   generator. Treat anything trained on it as a pipeline smoke test.
2. **All 20 ragas appear exactly once**, so raga conditioning has no
   within-raga variation to learn from at all.
3. **Five composers have fewer than 3 compositions.**
4. **Bhairavi loses a note.** It is bhashanga (D2 ascending, D1 descending) but
   the record declares mela 20, which only yields D1. The source notation does
   not distinguish them either, so the arohana D2 is unrecoverable; the caveat
   is recorded in `config/raga_normalization.json`.
5. **One genuine notation error**: `hindolam_keerthanam_001` uses `R` in its
   Anupallavi, but Hindolam has no rishabha. Flagged, record kept, not guessed.
6. **`Unknown / Unclassified` is train-only.** At n=20, an exact 80/10/10 split
   leaves 2 records each for val and test; those slots go to Trinity and to
   Other Known Composers so that Trinity is evaluable.

## Composer grouping

Trinity membership is asserted explicitly in `config/composer_normalization.json`
and is never inferred from spelling similarity (PRD section 2). A name not in
the dictionary is kept verbatim and grouped `Unknown / Unclassified`; hedged
attributions such as `"Purandaradasa (attributed)"` keep the canonical name but
are downgraded to `certainty: attributed`, with the original string always
retained in `composer_raw`.
