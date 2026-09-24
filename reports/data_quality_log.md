# Data-quality log

Generated: 2026-09-23T18:07:39+00:00

- Total events: **68**
- Errors: **0** | Warnings: **13** | Info: **55**
- Records touched by at least one event: **17**

## Events by code

| Code | Severity | Count | Stage |
| --- | --- | ---: | --- |
| `sparse_composer_class` | warning | 5 | validate |
| `length_unusually_long` | warning | 2 | clean |
| `sparse_raga_classes` | warning | 2 | validate |
| `dataset_small` | warning | 2 | validate |
| `note_outside_raga_scale` | warning | 1 | clean |
| `stratum_train_only` | warning | 1 | split |
| `punctuation_folded` | info | 11 | clean |
| `split_composition` | info | 6 | split |
| `jsonl_written` | info | 6 | split |
| `artifact_written` | info | 4 | pipeline |
| `stratum_allocated` | info | 4 | split |
| `period_undated` | info | 3 | normalize |
| `composer_alias_mapped` | info | 3 | normalize |
| `output_rows` | info | 2 | clean, normalize |
| `composer_attribution_hedged` | info | 2 | normalize |
| `tala_alias_mapped` | info | 2 | normalize |
| `lyrics_absent` | info | 2 | normalize |
| `statistics_computed` | info | 2 | validate |
| `leakage_check_passed` | info | 2 | split |
| `raw_loaded` | info | 1 | pipeline |
| `input_rows` | info | 1 | clean |
| `length_fence` | info | 1 | clean |
| `raga_musicological_note` | info | 1 | normalize |
| `raga_alias_mapped` | info | 1 | normalize |
| `trinity_subset` | info | 1 | normalize |

## Detail

### `sparse_composer_class` (5)

- _dataset_ - [full] composer 'Syama Sastri' has only 2 composition(s); too few to condition on reliably
- _dataset_ - [full] composer 'Purandaradasa' has only 2 composition(s); too few to condition on reliably
- _dataset_ - [full] composer 'Lalgudi Jayaraman' has only 1 composition(s); too few to condition on reliably
- _dataset_ - [full] composer 'Pachimiriam Adiyappiah' has only 1 composition(s); too few to condition on reliably
- _dataset_ - [trinity] composer 'Syama Sastri' has only 2 composition(s); too few to condition on reliably

### `length_unusually_long` (2)

- `jayakaru_geetam_dhanyasi_001` - 67 swaras is outside the fence [23.4, 64.4] (field: `n_swaras`)
- `nattai_varnam_001` - 68 swaras is outside the fence [23.4, 64.4] (field: `n_swaras`)

### `sparse_raga_classes` (2)

- _dataset_ - [full] 20 of 20 ragas appear exactly once; raga conditioning cannot generalise from one example
- _dataset_ - [trinity] 8 of 8 ragas appear exactly once; raga conditioning cannot generalise from one example

### `dataset_small` (2)

- _dataset_ - [full] 20 compositions is far below what a composer-conditioned generator needs; treat any trained model as a pipeline smoke test rather than a musical result
- _dataset_ - [trinity] 8 compositions is far below what a composer-conditioned generator needs; treat any trained model as a pipeline smoke test rather than a musical result

### `note_outside_raga_scale` (1)

- `hindolam_keerthanam_001` - notation uses swaras absent from the declared scale: R x1 (field: `sections_json`)

### `stratum_train_only` (1)

- _dataset_ - [full] Unknown / Unclassified (5 compositions) received no holdout slots, so it is absent from val and test; at this dataset size the 80/10/10 target cannot cover every group

### `punctuation_folded` (11)

- `bilahari_kriti_suryamurthe_001` - repaired source: punctuation_folded (field: `source`)
- `charukesi_kriti_001` - repaired source: punctuation_folded (field: `source`)
- `kalyani_varnam_ata_001` - repaired source: punctuation_folded (field: `source`)
- `natabhairavi_kriti_001` - repaired source: punctuation_folded (field: `source`)
- `reethigowla_keerthanam_001` - repaired source: punctuation_folded (field: `source`)
- `sahana_kriti_001` - repaired source: punctuation_folded (field: `source`)
- `saveri_geetam_001` - repaired source: punctuation_folded (field: `source`)
- `shankarabharanam_alapana_001` - repaired source: punctuation_folded (field: `source`)
- `suddhasaveri_kriti_001` - repaired source: punctuation_folded (field: `source`)
- `varali_kriti_001` - repaired source: punctuation_folded (field: `source`)
- `vathapi_ganapathim_hamsadhvani_001` - repaired source: punctuation_folded (field: `source`)

### `split_composition` (6)

- _dataset_ - [full] train: 16 compositions (80%); composers: Muthuswami Dikshitar, Papanasam Sivan, Purandaradasa, Syama Sastri, Traditional, Tyagaraja
- _dataset_ - [full] val: 2 compositions (10%); composers: Lalgudi Jayaraman, Syama Sastri
- _dataset_ - [full] test: 2 compositions (10%); composers: Muthuswami Dikshitar, Pachimiriam Adiyappiah
- _dataset_ - [trinity] train: 6 compositions (75%); composers: Muthuswami Dikshitar, Syama Sastri, Tyagaraja
- _dataset_ - [trinity] val: 1 compositions (12%); composers: Syama Sastri
- _dataset_ - [trinity] test: 1 compositions (12%); composers: Muthuswami Dikshitar

### `jsonl_written` (6)

- _dataset_ - 16 records -> train.jsonl
- _dataset_ - 2 records -> val.jsonl
- _dataset_ - 2 records -> test.jsonl
- _dataset_ - 6 records -> trinity_train.jsonl
- _dataset_ - 1 records -> trinity_val.jsonl
- _dataset_ - 1 records -> trinity_test.jsonl

### `artifact_written` (4)

- _dataset_ - wrote cleaned_dataset.parquet
- _dataset_ - wrote normalized_dataset.parquet
- _dataset_ - wrote trinity_dataset.parquet
- _dataset_ - wrote dataset_statistics.json and dataset_report.md

### `stratum_allocated` (4)

- _dataset_ - [full] Other Known Composers: 5 train / 1 val / 1 test from 7 compositions
- _dataset_ - [full] Trinity: 6 train / 1 val / 1 test from 8 compositions
- _dataset_ - [full] Unknown / Unclassified: 5 train / 0 val / 0 test from 5 compositions
- _dataset_ - [trinity] Trinity: 6 train / 1 val / 1 test from 8 compositions

### `period_undated` (3)

- `bhairavi_tillana_001` - period_undated (field: `period`)
- `kharaharapriya_geetam_001` - period_undated (field: `period`)
- `shankarabharanam_alapana_001` - period_undated (field: `period`)

### `composer_alias_mapped` (3)

- `natabhairavi_kriti_001` - composer_alias_mapped:Thyagaraja->Tyagaraja (field: `composer`)
- `reethigowla_keerthanam_001` - composer_alias_mapped:Thyagaraja->Tyagaraja (field: `composer`)
- `sahana_kriti_001` - composer_alias_mapped:Thyagaraja->Tyagaraja (field: `composer`)

### `output_rows` (2)

- _dataset_ - 20 records survived cleaning (from 20)
- _dataset_ - 20 records normalised

### `composer_attribution_hedged` (2)

- `jayakaru_geetam_dhanyasi_001` - composer_attribution_hedged (field: `composer`)
- `sarali_varisai_mayamalavagowla_001` - composer_attribution_hedged (field: `composer`)

### `tala_alias_mapped` (2)

- `jayakaru_geetam_dhanyasi_001` - tala_alias_mapped:Chaturashra Dhruvam->Chaturasra Dhruva (field: `tala`)
- `kalyani_varnam_ata_001` - tala_alias_mapped:Ata->Khanda Ata (field: `tala`)

### `lyrics_absent` (2)

- `sarali_varisai_mayamalavagowla_001` - no lyrics on any section (kept as empty strings, not dropped) (field: `sections_json`)
- `shankarabharanam_alapana_001` - no lyrics on any section (kept as empty strings, not dropped) (field: `sections_json`)

### `statistics_computed` (2)

- _dataset_ - [full] 20 compositions, 8 composers, 8 Trinity, 20 ragas, 6 talas
- _dataset_ - [trinity] 8 compositions, 3 composers, 8 Trinity, 8 ragas, 3 talas

### `leakage_check_passed` (2)

- _dataset_ - [full] no composition appears in more than one split
- _dataset_ - [trinity] no composition appears in more than one split

### `raw_loaded` (1)

- _dataset_ - loaded 20 rows x 22 columns from train-00000-of-00001.parquet

### `input_rows` (1)

- _dataset_ - 20 raw records read

### `length_fence` (1)

- _dataset_ - swara-count fence [23.4, 64.4] from Q1=38.8, Q3=49.0

### `raga_musicological_note` (1)

- `bhairavi_tillana_001` - Bhashanga raga: takes D2 in arohana and D1 in avarohana. The parent mela (20) only yields D1, so arohana D2 is not recoverable from the mela alone. (field: `raga`)

### `raga_alias_mapped` (1)

- `vathapi_ganapathim_hamsadhvani_001` - raga_alias_mapped:Hamsadhvani->Hamsadhwani (field: `raga`)

### `trinity_subset` (1)

- _dataset_ - 8 Trinity compositions: Muthuswami Dikshitar 3, Syama Sastri 2, Tyagaraja 3

