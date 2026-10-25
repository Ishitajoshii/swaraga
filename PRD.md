# PRD — Raga-Conditioned Melodic Continuation

**Status:** approved, v1 in build
**Context:** academic / thesis
**Depends on:** the preprocessing pipeline in `src/swaraga/` (see `README.md`)

---

## 1. Objective

Given the preceding music of a Carnatic composition, generate the continuation
so that it **is unmistakably in the stated raga** and metrically well-formed.

The headline goal is *4 avartanas in, 2 avartanas out*. The corpus cannot
support that today, so the task is staged as a ladder (§3) whose first rungs are
buildable now and whose top rung unlocks as repertoire arrives.

### 1.1 Why this is not a generic sequence-modelling problem

A raga is not a scale. It is a scale **plus** characteristic phrases
(prayogas), resting notes (nyasa), emphasised notes (jeeva), direction-dependent
note choice (vakra), and ornamentation (gamaka). A model that merely emits
in-scale notes produces something a musician will reject immediately.

This PRD therefore splits the problem in three:

| Sub-problem | Solved by | Needs data? |
| --- | --- | --- |
| **Are the notes in the raga?** | the scale-degree representation (§4) | **No** |
| **Is the motion legal?** | the decode-time transition mask (§7) | **No** |
| **Is it musical?** | the learned model | **Yes** |

Note the first two rows have *different* mechanisms, and the distinction is
easy to get wrong. Because degrees are mapped back to swaras modulo the raga's
own scale, an out-of-raga note is **literally unrepresentable** — note-level
conformance is a property of the encoding, and the mask cannot improve a number
that is already structurally 1.000.

What the mask actually buys is **legal motion**: a raga's ascending and
descending paths differ, and nothing in the degree encoding forces a model to
respect that asymmetry. Measured in §10 experiment 3.

Either way, both are settled without data, which frees every experiment to
measure the part that actually needs evidence.

---

## 2. The data situation (read this before anything else)

Measuring the existing 20-composition corpus against the headline task:

| Question | Answer |
| --- | --- |
| 4→2 avartana training examples available | **~14** |
| Compositions long enough to yield even one | **6 of 20** |
| Mean avartanas per composition | 4.1 (a complete kriti runs 15–30) |
| Compositions per raga | **1, for all 20 ragas** |
| Per-raga bigram coverage of its own legal transitions | 15–37% |
| Distinct swara bigrams, whole corpus | 102 |

Two conclusions:

1. The corpus is short by roughly **two orders of magnitude**.
2. Its entries are **truncated fragments**, not complete compositions. "Get
   more data" specifically means *more complete compositions*, not more rows.

### 2.1 Gating task — verify provenance

Several signals suggest this corpus may be **machine-generated rather than
authentic repertoire**:

- `sa_hz` is exactly `240.0` for all 20 rows
- every note in every composition carries the identical `GMK_AHAT` tag
- swara variant digits ignore the raga (`_2` almost everywhere)
- `features` are programmatic just-intonation ratios
- one `source` reads `"References/Jayakaru-Geetam.docx + References/NOTATION_STANDARDS.md"`
- **`hindolam_keerthanam_001` contains a rishabha** — Hindolam has none; no
  authentic source would do this
- "Vathapi Ganapathim" appears as 2.8 avartanas; the actual kriti is far longer

**This must be resolved before any result is reported.** Trace the origin of
the 20 compositions and spot-check three against a published notation. The
pipeline and this architecture survive either outcome — they simply need real
input. Building a thesis on fabricated notation would not survive review.

---

## 3. Task ladder

Every rung shares one architecture; only the prediction horizon changes.

| Rung | Task | Windows available now | Role |
| --- | --- | ---: | --- |
| **T1** | 12 notes → next 4 | 718 | unit-test rung |
| **T2** | 16 notes → next 8 (½ avartana) | 558 | **v1 target** |
| **T3** | 4 avartanas → next 2 | 59 | headline goal |

T3's 59 windows come from only **6 of 20 compositions and cover 6 ragas**, with
33 of them from a single piece — so the rung runs, but nothing trained on it
today would mean anything. (At stride 1 *avartana* rather than 1 note it yields
just 14.)

**T2 is the v1 target.** T1's four-note horizon is too short to evaluate
musically — no rater can answer "is this Mohanam?" from four notes — so T1
exists to exercise the plumbing. T3 remains the goal and becomes reachable as
the data plan (§6) delivers.

Windows are cut at **stride 1 note** and never cross a composition boundary.

### 3.1 Formal definition

```
input :  context   c = (s₁ … s_k)        k = 12 (T1) | 16 (T2) | 4 avartanas (T3)
         condition r = raga
                   t = tala, kala
                   a = composer            (optional)
output:  y = (s_{k+1} … s_{k+h})          h = 4 | 8 | 2 avartanas
constraint: every sᵢ ∈ y is legal in r, and |y| is exactly h
```

---

## 4. Modelling space — scale degrees, not absolute swaras

Per-raga data is ~36 windows even at T1, far too few to learn any raga's
character in absolute swaras. The model therefore works in **scale-degree
space**: each swara maps to its index in that raga's own scale, all ragas pool
into a single training set, and the grammar re-instantiates degrees into the
target raga's actual swaras at decode time.

```
Mohanam    S  R2 G3 P  D2   →  0 1 2 3 4
Hindolam   S  G2 M1 D1 N2   →  0 1 2 3 4     ← same contour, shared evidence
```

This is what makes the current corpus usable at all: **143 degree 4-grams
recur** across ragas, where per-raga absolute modelling has almost no
repetition.

**Known cost, stated plainly.** A degree model captures *contour*, not *raga
identity*. Expect "generic pentatonic contour relabelled as Mohanam" until
per-raga data grows. Quantifying that gap is experiment 4 in §9 — a thesis
result, not a failure.

---

## 5. Target ragas

**Mohanam, Hamsadhwani, Hindolam, Abhogi, Suddha Saveri.**

All five are pentatonic (audava), so the state space is roughly half that of a
sampurna raga — materially less data needed per raga for the same quality. All
five already appear in the corpus and all have large public repertoire.

---

## 6. Data requirements

| Tier | Comps/raga | Total | ~T2 windows | Unlocks |
| --- | ---: | ---: | ---: | --- |
| **Have now** | 1 | 20 | ~560 | T1/T2 baselines, first scaling point |
| Floor | 10 | 50 | ~1,400 | per-raga modelling starts to work |
| Target | 40 | 200 | ~5,600 | neural models; **T3 becomes viable** |
| Comfortable | 100 | 500 | ~14,000 | ablations with tight error bars |

Data acquisition gates *raga-specific quality* and T3 — **not the start of
work**. Requirement is **complete compositions**, not fragments.

### 6.1 Acquisition plan

1. **Parse public notation collections** — highest yield per hour. One parser
   per source format, emitting the existing schema. **Gated on a licence
   review**, since provenance must be defensible in a thesis.
2. **Synthetic from raga grammar** — varisai / alankara / tana patterns over
   arohanam–avarohanam. Unlimited volume, for **pretraining only**.
   *Hard rule: synthetic data never appears in validation or test.*
3. **Manual transcription** — reserved for the ~50-item gold evaluation set,
   where fidelity matters most.
4. **Audio corpora (CompMusic / Saraga)** — **out of scope for v1.**
   Audio-to-symbolic transcription is a research project in itself.

---

## 7. Architecture

```
  context + (raga, tala)
           │
           ▼
   ┌───────────────┐
   │ sequence model│ ──── scores over scale degrees
   └───────────────┘
           │
           ▼
   ┌───────────────────────────────┐
   │      constrained decoder      │
   │  ┌─────────────┐              │
   │  │ RagaGrammar │─ transition  │ ──▶  continuation
   │  ├─────────────┤    mask       │      legal motion
   │  │ TalaTemplate│─ length /     │      exact length
   │  └─────────────┘    position   │
   └───────────────────────────────┘
```

| Component | Responsibility |
| --- | --- |
| `RagaGrammar` | legal swaras; legal ascending vs descending transitions from arohanam/avarohanam; vakra handling; nyasa and jeeva swaras |
| `TalaTemplate` | exact position count; anga boundaries; where long notes and rests may fall |
| constrained decoder | masks illegal *transitions* before sampling, and fixes the output length. Note-level conformance comes from the degree encoding instead (§1.1) |

`arohanam` and `avarohanam` already land in `normalized_dataset.parquet` as
resolved variant lists, so `RagaGrammar` builds directly on existing output.

---

## 8. Model roadmap

| ID | Model | Stack |
| --- | --- | --- |
| **B0** | raga-grammar random walk — the floor | numpy |
| **B0.5** | "continue the current direction" heuristic | numpy |
| **B1** | variable-order Markov over scale degrees, with backoff | numpy |
| **B2** | retrieval + adaptation — nearest context by contour | numpy |
| **M1** | conditional GRU (~90k params) and Transformer (~309k), constrained decoding | PyTorch |
| **M2** | synthetic-pretrained → fine-tuned on real repertoire | PyTorch |

### 8.0 Measured result (T2, seed 42)

B1 beats both neural models: contour 1.11 vs 1.39 (GRU) and 1.40
(Transformer). At the shorter T1 horizon the GRU instead wins on exact match
(0.53 vs 0.46) and perplexity (2.1 vs 2.2), while B1 keeps the contour lead.

This is the pre-registered finding, not a disappointment: at ~500 effective
training examples an n-gram is the right tool, and the question the thesis
answers is *how much data changes that* (§10 experiment 1).

### 8.1 B0.5 is the bar, and it is a high one

**16% of all 4-grams in this corpus are pure scalar runs** (`3 2 1 0`,
`4 3 2 1`, `6 5 4 3`, `5 4 3 2`, `2 3 4 5`), because the corpus is heavy on
geetams and varisais. A "continue the current direction" heuristic is therefore
a genuinely strong baseline.

**Any learned model that fails to beat B0.5 is not contributing.** Reporting
that honestly is a legitimate result and feeds directly into the scaling
argument.

### 8.2 Tech stack

- **B0–B2: pure Python + numpy.** Counts, backoff and retrieval need no
  framework, and this keeps the baselines trivially auditable for a committee.
- **M1–M2: PyTorch 2.x, CPU-only.** Custom constrained decoding is far cleaner
  in a raw decode loop than through a framework's `generate()`.
- **No GPU required.** At T2 the model is ~1M params (2–4 layers, `d_model`
  128, vocab ~15–25) over ~558 windows — minutes per run on CPU. The scaling
  study needs dozens of runs across tiers and seeds; cheap runs are what make
  it feasible.
- **Deliberately not used:** HuggingFace Transformers (pretrained weights are
  useless for swara tokens, and the abstraction obstructs custom masking);
  TensorFlow / JAX (no benefit here).
- **Overfitting caveat:** at 558 windows a transformer overfits almost
  immediately. M1 starts as a small LSTM or fixed-context MLP; the transformer
  appears only when a data tier justifies it, chosen by validation loss rather
  than by default.
- `torch` enters `requirements.txt` only at the M1 milestone, so the
  preprocessing pipeline keeps its light dependency set.

---

## 9. Evaluation

### 9.1 Automatic metrics

| Metric | Definition | Expected |
| --- | --- | --- |
| Raga conformance | % generated notes in the raga's legal set | 100% - **structural**, see 1.1 |
| Transition legality | % bigrams legal per arohana/avarohana direction | 100% under the mask |
| Length exactness | output length == requested horizon | 100% by construction |
| Nyasa appropriateness | % continuations ending on a resting swara | learned |
| Held-out perplexity | per-token NLL on unseen compositions | learned |
| Contour distance | DTW between generated and ground-truth degree contour | learned |
| **Novelty** | max n-gram overlap with the training set | **must be < 1.0** |

The first three are contract checks, not results. The interesting numbers are
the last four.

Raga conformance in particular is **not evidence that anything works** - it is
1.000 even for an untrained random walk, and even with the mask switched off,
because the degree encoding cannot express an out-of-raga note. Quote
transition legality instead when the question is what the grammar contributes.

**Novelty is non-negotiable at this data scale.** A model that memorises 20
melodies scores perfectly on every other metric and is worthless. Novelty is
reported alongside every single result.

### 9.2 Human evaluation — the thesis's primary evidence

- ~50 generated continuations, ≥2 Carnatic musicians as raters
- **Likert (1–5):** musicality; continuity with the given context
- **Forced-choice raga identification:** shown only the generated phrase, can a
  musician name the raga? This is the sharpest available test of whether
  "matching the raga" was actually achieved, as opposed to merely satisfying
  the scale constraint.
- Inter-rater agreement reported

---

## 10. Experiments

1. **Data-scaling study** — train at 1 / 5 / 10 / 20 / 40 compositions per
   raga; plot quality against repertoire size.
   *This is the thesis's main contribution:* it answers **how much repertoire
   raga-conditioned generation actually needs**. The first point is measurable
   today.
2. **Horizon study** — quality vs prediction length (T1 → T2 → T3). Shows how
   far ahead a model stays musical; itself a scarcity result.
3. **Constraint ablation** — constrained vs unconstrained decoding, reported on
   **transition legality**. Raga conformance is structurally 1.000 in both
   arms (§1.1), so reporting it there would overstate the grammar's value.
4. **Degree-pooling ablation** — pooled scale-degree model vs per-raga absolute
   model. Quantifies the contour-versus-character trade-off from §4.
5. **Raga-complexity comparison** — pentatonic vs sampurna at equal data.

---

## 11. Success criteria

**v1 (T2, current data)**
- Every generated continuation is in-raga and of exact length, across all seeds
- B1 or B2 beats B0.5 on held-out perplexity and contour distance
- Novelty < 1.0 for every reported model
- Scaling study has its first data point

**v2 (T3, target data tier)**
- T3 runs end-to-end on real repertoire
- Musicians identify the intended raga above chance in forced choice
- Mean musicality ≥ 3/5

**Publishable regardless:** the scaling curve and the honest account of what a
20-composition corpus can and cannot support.

---

## 12. Risks

| Risk | Mitigation |
| --- | --- |
| **Corpus provenance unverified** (§2.1) — fatal for a thesis if fabricated | **Gating task** before any modelling: trace origin, spot-check 3 against published notation |
| Data acquisition stalls | T1/T2 baselines run on current data; synthetic pretraining keeps modelling unblocked; scaling study publishable at low N |
| Learned model never beats B0.5 | Reported as a finding, not hidden; motivates the scaling argument |
| Constraint makes the task look trivial | Ablation quantifies it; musicality is human-judged and not constraint-satisfiable |
| Model memorises 20 melodies | Novelty metric reported with every result |
| No raters available | Automatic metrics pre-registered as fallback primary |
| Licensing unclear | Licence review gates any scraping |

---

## 13. Out of scope for v1

- Lyrics generation — the schema is designed so lyrics can be added later as a
  second conditioning stream, but v1 generates swaras only
- Gamaka realisation and audio synthesis
- Audio-to-symbolic transcription
- Sampurna (7-note) ragas beyond the complexity comparison
- Real-time or interactive use

---

## 14. Deliverables

| Path | Purpose |
| --- | --- |
| `config/raga_grammar.json` | nyasa / jeeva / vakra / prayogas for the 5 target ragas |
| `src/swaraga/grammar.py` | `RagaGrammar`, `TalaTemplate` |
| `src/swaraga/windows.py` | T1/T2/T3 windowing + scale-degree encoding, leakage-safe |
| `src/swaraga/decode.py` | constrained decoder |
| `src/swaraga/models/` | `baseline_heuristic.py`, `baseline_ngram.py`, `retrieval.py`; `neural.py` at M1 |
| `src/swaraga/synth.py` | synthetic raga-conformant generator |
| `src/swaraga/evaluate.py` | metric suite |
| `scripts/run_experiments.py` | reproduces every reported number |
| `reports/` | baseline results, scaling curve |

**Reused as-is:** `melakarta.py`, `notation.py`, `normalizers/`, `config/*.json`,
`split.py` (extended to window level), `quality_log.py`.
