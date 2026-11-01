"""Recording metadata and ordered, raga-filtered library selection."""

# Reviewed Ninnu Kori and Mohanam practice recordings.
# Keep related material grouped; all six entries are prepared bank examples.
RECORDINGS: list[dict[str, str]] = [
    {
        "id": "ninnu_kori_pair01", "title": "Ninnu Kori - pallavi lines 1 to 2",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/ninnu_kori_pair01_seed.wav",
        "response_path": "data/audio/ninnu_kori_pair01_response.wav",
        "source_take": "standard_recording_29", "split": "bank",
    },
    {
        "id": "ninnu_kori_pair02", "title": "Ninnu Kori - pallavi lines 2 to 3",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/ninnu_kori_pair02_seed.wav",
        "response_path": "data/audio/ninnu_kori_pair02_response.wav",
        "source_take": "standard_recording_29", "split": "bank",
    },
    {
        "id": "ninnu_kori_pair03", "title": "Ninnu Kori - pallavi lines 3 to 4",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/ninnu_kori_pair03_seed.wav",
        "response_path": "data/audio/ninnu_kori_pair03_response.wav",
        "source_take": "standard_recording_29", "split": "bank",
    },
    {
        "id": "mohanam_take30", "title": "Mohanam practice 1",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/mohanam_take30_timed_seed.wav",
        "response_path": "data/audio/mohanam_take30_timed_response.wav",
        "source_take": "standard_recording_30", "split": "bank",
    },
    {
        "id": "mohanam_take31", "title": "Mohanam practice 2",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/mohanam_take31_timed_seed.wav",
        "response_path": "data/audio/mohanam_take31_timed_response.wav",
        "source_take": "standard_recording_31", "split": "bank",
    },
    {
        "id": "mohanam_take32", "title": "Mohanam practice 3",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/mohanam_take32_seed.wav",
        "response_path": "data/audio/mohanam_take32_response.wav",
        "source_take": "standard_recording_32", "split": "bank",
    },
]

# Example SHAPE ONLY: do not uncomment without replacing values with real metadata.
# {
#     "id": "mohanam_seed01_optionA",
#     "title": "Mohanam — seed 1, response A",
#     "raga": "Mohanam",
#     "tala": "Adi",
#     "seed_path": "data/audio/mohanam_seed01_optionA_seed.wav",
#     "response_path": "data/audio/mohanam_seed01_optionA_response.wav",
#     "source_take": "mohanam_seed01_optionA_take01",
#     "split": "bank",  # or "evaluation", according to the dataset split
# },


def list_recordings(
    records: list[dict[str, str]], raga: str | None = None
) -> list[dict[str, str]]:
    """Select bank records, optionally restricted to one exact raga name."""
    selected = []  # a brand-new list, so the input list is never changed
    for record in records:
        if record["split"] != "bank":
            continue  # skip "evaluation" (or anything else that isn't "bank")
        if raga is not None and record["raga"] != raga:
            continue  # a raga was requested and this record's raga is different
        selected.append(record)  # keeps the original order
    return selected


def _check() -> None:
    """Validate filtering and input preservation without loading audio."""
    examples = [
        {"id": "a", "raga": "Mohanam", "split": "bank"},
        {"id": "b", "raga": "Mohanam", "split": "evaluation"},
        {"id": "c", "raga": "Hamsadhwani", "split": "bank"},
        {"id": "d", "raga": "Mohanam", "split": "bank"},
    ]
    before = [entry.copy() for entry in examples]
    assert [entry["id"] for entry in list_recordings(examples)] == ["a", "c", "d"]
    assert [entry["id"] for entry in list_recordings(examples, "Mohanam")] == ["a", "d"]
    assert list_recordings(examples, "Unknown raga") == []
    assert list_recordings(examples, "mohanam") == []
    assert list_recordings([]) == []
    assert examples == before, "Do not change the input records."
    bank_only = [examples[0]]
    assert list_recordings(bank_only) is not bank_only, "Return a new list."


if __name__ == "__main__":
    _check()