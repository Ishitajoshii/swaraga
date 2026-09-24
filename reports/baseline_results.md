# Baseline results

Seed 42. Reproduce with `python scripts/run_experiments.py`.

Contract checks (`raga_conformance`, `transition_legality`,
`length_exact`) are guaranteed by the constrained decoder and read
1.00 for every model including the random walk - they verify the
system, they do not rank models. The columns that rank models are
`contour_distance` (lower is better), `exact_match`, `nyasa` and
`perplexity`.

**`GT` is the ground truth**, scored as if it were a model. Read
every row against it, not against a theoretical ideal - most
importantly `novelty`, where real human continuations score only
~0.12 because the degree vocabulary is 15 symbols wide and the
repertoire is formulaic. Heavy n-gram reuse is normal music here.

## T1 - 12 notes -> next 4

718 windows from 20 compositions covering 20 ragas.

| Model | n | conform | legal | len | nyasa | contour dist | exact | novelty | ppl |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GT | 66 | 1.00 | 1.00 | 1.00 | 0.55 | 0.00 | 1.00 | 0.12 | - |
| B0 | 66 | 1.00 | 1.00 | 1.00 | 0.42 | 3.41 | 0.07 | 0.98 | - |
| B0.5 | 66 | 1.00 | 1.00 | 1.00 | 0.45 | 1.20 | 0.23 | 0.82 | - |
| B1 | 66 | 1.00 | 1.00 | 1.00 | 0.55 | 0.90 | 0.46 | 0.20 | 2.2 |
| B2 | 66 | 1.00 | 1.00 | 1.00 | 0.45 | 1.40 | 0.36 | 0.70 | - |
| M1-gru | 66 | 1.00 | 1.00 | 1.00 | 0.58 | 1.12 | 0.53 | 0.26 | 2.1 |
| M1-transformer | 66 | 1.00 | 1.00 | 1.00 | 0.52 | 1.14 | 0.50 | 0.29 | 3.1 |

## T2 - 16 notes -> next 8 (half avartana)

558 windows from 20 compositions covering 20 ragas.

| Model | n | conform | legal | len | nyasa | contour dist | exact | novelty | ppl |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| GT | 50 | 1.00 | 1.00 | 1.00 | 0.50 | 0.00 | 1.00 | 0.13 | - |
| B0 | 50 | 1.00 | 1.00 | 1.00 | 0.42 | 3.21 | 0.09 | 1.00 | - |
| B0.5 | 50 | 1.00 | 1.00 | 1.00 | 0.36 | 1.45 | 0.15 | 0.87 | - |
| B1 | 50 | 1.00 | 1.00 | 1.00 | 0.56 | 1.11 | 0.32 | 0.16 | 2.3 |
| B2 | 50 | 1.00 | 1.00 | 1.00 | 0.38 | 1.52 | 0.22 | 0.76 | - |
| M1-gru | 50 | 1.00 | 1.00 | 1.00 | 0.50 | 1.39 | 0.26 | 0.38 | 2.4 |
| M1-transformer | 50 | 1.00 | 1.00 | 1.00 | 0.58 | 1.40 | 0.25 | 0.48 | 4.8 |

