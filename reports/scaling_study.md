# Scaling study and constraint ablation

Rung T2. Neural points averaged over 5 seeds (42, 43, 44, 45, 46); baselines are deterministic.

## Why the x-axis is compositions, not windows

Stride-1 windows from N compositions overlap almost entirely, so a
window count badly overstates how much independent data a model saw.
The whole corpus is ~907 swaras. Compositions are the honest unit.

## Scaling curve

| Compositions | Windows | Model | contour dist | exact | novelty | ppl | overfit gap |
| ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 2 | 58 | B0 | 3.21 | 0.09 | 1.00 | - | - |
| 2 | 58 | B0.5 | 1.45 | 0.15 | 0.92 | - | - |
| 2 | 58 | B1 | 1.12 | 0.34 | 0.30 | 2.8 | - |
| 2 | 58 | B2 | 1.57 | 0.18 | 0.81 | - | - |
| 2 | 58 | M1-gru | 1.33 ± 0.14 | 0.30 | 0.50 | 2.9 | +1.04 |
| 2 | 58 | M1-transformer | 1.56 ± 0.15 | 0.23 | 0.65 | 4.2 | +1.06 |
| 4 | 136 | B0 | 3.21 | 0.09 | 1.00 | - | - |
| 4 | 136 | B0.5 | 1.45 | 0.15 | 0.91 | - | - |
| 4 | 136 | B1 | 1.11 | 0.36 | 0.24 | 2.5 | - |
| 4 | 136 | B2 | 1.65 | 0.17 | 0.87 | - | - |
| 4 | 136 | M1-gru | 1.48 ± 0.07 | 0.28 | 0.55 | 2.6 | +0.68 |
| 4 | 136 | M1-transformer | 1.67 ± 0.20 | 0.21 | 0.74 | 4.0 | +0.57 |
| 8 | 246 | B0 | 3.21 | 0.09 | 1.00 | - | - |
| 8 | 246 | B0.5 | 1.45 | 0.15 | 0.90 | - | - |
| 8 | 246 | B1 | 1.29 | 0.33 | 0.24 | 2.2 | - |
| 8 | 246 | B2 | 1.46 | 0.22 | 0.76 | - | - |
| 8 | 246 | M1-gru | 1.35 ± 0.04 | 0.29 | 0.42 | 2.3 | +0.33 |
| 8 | 246 | M1-transformer | 1.33 ± 0.13 | 0.24 | 0.57 | 3.3 | +0.39 |
| 16 | 466 | B0 | 3.21 | 0.09 | 1.00 | - | - |
| 16 | 466 | B0.5 | 1.45 | 0.15 | 0.87 | - | - |
| 16 | 466 | B1 | 1.11 | 0.32 | 0.16 | 2.3 | - |
| 16 | 466 | B2 | 1.52 | 0.22 | 0.76 | - | - |
| 16 | 466 | M1-gru | 1.27 ± 0.08 | 0.30 | 0.36 | 2.2 | +0.04 |
| 16 | 466 | M1-transformer | 1.17 ± 0.13 | 0.29 | 0.39 | 3.0 | +0.37 |

## Constraint ablation

> **SUPERSEDED — do not quote this table.** It is left over from an earlier
> run, before the ablation was corrected. Regenerate it with
> `python scripts/run_scaling_study.py`; the code is already fixed.
>
> The framing below is wrong: raga conformance reads 1.000 in *both* arms
> because degrees map back to swaras modulo the raga's own scale, so an
> out-of-raga note is unrepresentable. Conformance is a property of the
> encoding, not something the mask achieves. The corrected ablation reports
> **transition legality**, which is what the mask actually constrains.
>
> The contour column is still informative: constrained decoding beats
> unconstrained (1.27 vs 1.42 GRU, 1.17 vs 1.28 Transformer), so the mask does
> help — just not via the column this table highlights.

What the raga grammar actually buys. Unconstrained decoding samples
straight from the model with no mask; the conformance column is the
fraction of generated notes that are genuinely in the raga.

| Model | Decoding | raga conformance | contour dist |
| --- | --- | ---: | ---: |
| M1-gru | constrained | 1.000 ± 0.000 | 1.27 |
| M1-gru | unconstrained | 1.000 ± 0.000 | 1.42 |
| M1-transformer | constrained | 1.000 ± 0.000 | 1.17 |
| M1-transformer | unconstrained | 1.000 ± 0.000 | 1.28 |

