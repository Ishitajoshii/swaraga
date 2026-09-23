# Swaraga - Carnatic composition dataset preprocessing

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

## Honest limits of this data

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
