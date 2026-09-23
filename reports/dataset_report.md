# Dataset statistics

Computed from `data/processed/normalized_dataset.parquet`.

## Headline

| Metric | Value |
| --- | ---: |
| Compositions | 20 |
| Unique composers | 8 |
| Trinity compositions | 8 |
| Unique ragas | 20 |
| Unique talas | 6 |
| Unique melakartas | 10 |
| Mean sequence length | 50.9 |
| Median sequence length | 51.5 |
| Shortest / longest | 32 / 84 |
| Total swara tokens | 907 |
| Swara vocabulary size | 24 |
| Full token vocabulary size | 41 |

## Distribution by composer group

| Group | Count |
| --- | ---: |
| Trinity | 8 |
| Other Known Composers | 7 |
| Unknown / Unclassified | 5 |

## Distribution by composer

| Composer | Count |
| --- | ---: |
| Traditional | 5 |
| Muthuswami Dikshitar | 3 |
| Papanasam Sivan | 3 |
| Tyagaraja | 3 |
| Purandaradasa | 2 |
| Syama Sastri | 2 |
| Lalgudi Jayaraman | 1 |
| Pachimiriam Adiyappiah | 1 |

## Trinity breakdown

| Composer | Count |
| --- | ---: |
| Muthuswami Dikshitar | 3 |
| Tyagaraja | 3 |
| Syama Sastri | 2 |

## Distribution by tala

| Tala | Count |
| --- | ---: |
| Adi | 12 |
| Rupaka | 3 |
| Misra Chapu | 2 |
| Chaturasra Dhruva | 1 |
| Free (Alapana) | 1 |
| Khanda Ata | 1 |

## Distribution by raga

| Raga | Count |
| --- | ---: |
| Abhogi | 1 |
| Bhairavi | 1 |
| Bilahari | 1 |
| Charukesi | 1 |
| Dhanyasi | 1 |
| Hamsadhwani | 1 |
| Hindolam | 1 |
| Kalyani | 1 |
| Kharaharapriya | 1 |
| Mayamalavagowla | 1 |
| Mohanam | 1 |
| Natabhairavi | 1 |
| Nattai | 1 |
| Reethigowla | 1 |
| Sahana | 1 |
| Saveri | 1 |
| Shankarabharanam | 1 |
| Suddha Saveri | 1 |
| Todi | 1 |
| Varali | 1 |

## Composer attribution certainty

| Certainty | Count |
| --- | ---: |
| attested | 14 |
| traditional | 4 |
| attributed | 2 |

## Sequence-length flags

| Flag | Count |
| --- | ---: |
| ok | 18 |
| unusually_long | 2 |

## Swara vocabulary

| Token | Count |
| --- | ---: |
| P | 126 |
| M1 | 115 |
| [REST] | 111 |
| S | 106 |
| S' | 91 |
| R2 | 65 |
| G3 | 61 |
| N2 | 60 |
| G2 | 56 |
| D1 | 55 |
| N3 | 48 |
| D2 | 39 |
| R1 | 31 |
| R2' | 15 |
| M2 | 13 |
| R3 | 8 |
| G1 | 7 |
| G3' | 3 |
| N3' | 2 |
| R3' | 2 |
| D1' | 1 |
| M1' | 1 |
| N2' | 1 |
| P' | 1 |

## Duplicates

| Check | Count |
| --- | ---: |
| Duplicate ids | 0 |
| Duplicate titles | 0 |
| Duplicate swara sequences | 0 |

## Missing values

| Column | Missing / empty |
| --- | ---: |
| `composer_attribution_note` | 19 |
| `composer_birth_year` | 9 |
| `composer_death_year` | 9 |
| `period_century` | 3 |

## Lyrics coverage

- With lyrics on at least one section: **18**
- Without any lyrics: **2**

