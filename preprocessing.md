PRD — Carnatic Music Dataset Cleanup & Preprocessing Pipeline
1. Objective

Build a clean, standardized, model-ready dataset from the raw Carnatic composition dataset for training a deep learning model that can generate new compositions conditioned on composer, raga, and tala.

2. Composer Categorization

The pipeline will preserve all composers in the original dataset while adding a composer_group field:

Trinity
Tyagaraja
Muthuswami Dikshitar
Syama Sastri
Other Known Composers
Unknown / Unclassified

This allows us to later train either:

a Trinity-specific model, or
a broader model covering multiple Carnatic composers.

We should not label someone as Trinity solely based on spelling/name similarity; composer normalization will use a controlled mapping.

3. Data Cleaning

For every composition:

Remove exact duplicate records.
Remove records with missing/invalid musical notation.
Normalize composer names and spelling variations.
Normalize raga names and spelling variations.
Normalize tala names.
Standardize swara notation.
Standardize octave markers.
Standardize rests, gamakas/ornamentation markers where represented.
Remove unnecessary whitespace and formatting characters.
Detect and flag unusually short/long sequences.
Preserve lyrics and metadata where available rather than deleting them.
4. Composer Normalization

Create a mapping such as:

Tyagaraja
Tyagaraja Swami
Sri Tyagaraja
→ Tyagaraja
Muthuswami Dikshitar
Muthuswamy Dikshitar
Dikshitar
→ Muthuswami Dikshitar
Syama Sastri
Shyama Sastri
Syama Sastrigal
→ Syama Sastri

The original value should also be retained in a separate field for traceability.

5. Musical Representation

Convert compositions into a consistent token representation:

S R G M | P D N S'

with special tokens where necessary:

[BOS]
[EOS]
[REST]
[OCTAVE_UP]
[OCTAVE_DOWN]

Each composition should ultimately have a machine-readable sequence such as:

{
  "composer": "Tyagaraja",
  "composer_group": "Trinity",
  "raga": "Kalyani",
  "tala": "Adi",
  "swara_sequence": ["S", "R2", "G3", "M2", "P", "D2", "N3", "S'"]
}
6. Dataset Validation

Generate statistics after cleaning:

Number of compositions
Number of unique composers
Number of Trinity compositions
Number of unique ragas
Number of unique talas
Average composition length
Missing-value counts
Duplicate counts
Distribution by composer/raga

This will help us identify whether the Trinity classes are sufficiently represented before training.

7. Train/Validation/Test Split

Split by composition, not individual note sequences.

Recommended:

80% Train
10% Validation
10% Test

Avoid putting fragments from the same composition into multiple splits, as that would cause data leakage.

For the Trinity subset, ensure each composer is represented across the splits where the dataset size permits.

8. Model-Ready Dataset

Final files:

raw_dataset.parquet
        ↓
cleaned_dataset.parquet
        ↓
normalized_dataset.parquet
        ↓
train.jsonl
val.jsonl
test.jsonl

Each training example should contain:

composer
composer_group
raga
tala
swara_sequence
9. Final Generation Objective

The cleaned dataset should ultimately support prompts like:

Composer: Tyagaraja
Raga: Kalyani
Tala: Adi
→ Generate composition
Composer: Muthuswami Dikshitar
Raga: Hamsadhwani
Tala: Adi
→ Generate composition
Composer: Syama Sastri
Raga: Bhairavi
Tala: Misra Chapu
→ Generate composition

This gives us a composer-conditioned Carnatic music generator, rather than simply a generic next-note generator.

10. Deliverables

By the end of preprocessing:

Cleaned master dataset
Trinity-filtered dataset
Composer normalization dictionary
Raga normalization dictionary
Tala normalization dictionary
Dataset statistics/report
Preprocessing Python script
Train/validation/test files
Data-quality log