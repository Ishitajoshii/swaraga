# Mohanam notation sources

The browser app uses 63 distinct printed notation
passages, containing 1,874 written swara attacks, from two source-attributed
Mohanam compositions:

| Composition | Composer / version | Tala in source | Passages | Note attacks |
| --- | --- | --- | ---: | ---: |
| [Mohana Rama](https://www.shivkumar.org/music/mOhanarAma.htm) | Tyagaraja / Ram Kaushik | Adi, 2 kalai | 36 | 1,265 |
| [Rama Ninnu Nammina](https://www.shivkumar.org/music/ramaninnunammina.htm) | Tyagaraja / Ram Kaushik | Adi; kalai not specified | 27 | 609 |

Both notation pages are hosted in Shivkumar Kalyanaraman's Carnatic Music
Krithi Archive. These are passages/variations from **two compositions**, not
63 independent compositions or newly recorded performances.

## What the model uses

Each accepted source paragraph becomes a sequence of pitch classes from
`S R2 G3 P D2`. Both letter cases denote the same pitch class here. Each
written swara contributes one attack; comma/semicolon duration marks never
become fabricated rests or repeated attacks. Exact duplicate pitch sequences
within a composition are excluded. Sequences are counted once and never joined
across printed variations, sections or compositions.

An additional variable-order Markov model learns these sequences when the demo
starts. Its pitch-class probabilities reweight the existing baseline's candidate
scores, using a fixed heuristic strength of 0.75 and a positive floor. The
existing baseline supplies octave candidates; the raga constraints and the
two-repeated-note playback preference still apply. This supplement models symbolic pitch order; it does not train a voice model.

The demo's 449 legacy overlapping training windows from 15 compositions are
reported separately from the 63 new passages. The new supplement is consumed
by `DemoService`; the historical preprocessing/experiment pipeline and its
published metrics are not rewritten or presented as new results.

## Source limits

The HTML pages do not consistently specify register. Underlines, case,
punctuation and barlines are preserved as source spans, but their duration
interpretation is not validated. Consequently this addition trains **pitch
order only**, not octave, beat duration, tala alignment, gamakas or lyrics.
Instrumental playback still uses uniform reference-note timing. Vocal retrieval
still uses existing reviewed recordings.

Pitch membership and extraction are checked in code. Source links and hashes
establish traceability, not expert approval of a transcription. No listening
evaluation or measured musical-quality improvement is claimed for this update.
The two new composition groups are training-only; none of their passages are
held-out evaluation examples. They are absent from the existing holdout titles
and IDs. Future evaluations must hold out whole composition groups, including
alternate versions of the same composition.

The older dataset still has unverified provenance. Modern transcription reuse
terms were not stated on these pages, so no license is inferred for this
supplement. Lyrics, translations, lesson recordings and complete source pages
are not distributed in the dataset.

## Files and reproduction

- `data/knowledge/sources.json`: URLs, versions, access date, encoding and hashes.
- `data/knowledge/mohanam_notation.json`: source spans, zero-based HTML paragraph
  locators, section labels, pitch sequences, exclusions and training groups.
- `reports/mohanam_knowledge.json`: import counts and exclusions.
- `src/swaraga/knowledge.py`: strict extraction, validation and model supplement.

The committed JSON works offline; no web request occurs at demo startup.
To rebuild, save the two source HTML files using the filenames in the manifest
into a local directory, then run:

```powershell
python scripts/import_mohanam_notation.py --source-dir .demo-artifacts/notation-sources
python scripts/check_demo.py
python -m pytest -q -p no:cacheprovider tests/test_knowledge.py tests/test_demo.py tests/test_models.py tests/test_decode.py
```

The importer rejects changed source hashes rather than silently accepting a
new edition. Review a changed source before updating its manifest hash.
Restart `python scripts/run_demo.py` after changing the supplement. The source
snapshot packager includes `data/knowledge` so packaged demos keep this addition.
