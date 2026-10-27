"""FRIEND 2: a tiny recording catalog filter (about 30–60 minutes).

You only need this file and Python. No audio package or big repo knowledge needed.
Use Python 3.10 or newer. You do not need to setup the whole repo.

YOUR SMALL CODING TASK TODAY
1. Complete list_recordings(records, raga=None). Return a NEW list containing
   only entries whose split is "bank". If raga is supplied, keep only entries
   whose raga exactly matches it. Preserve the original order; do not edit input.
2. A loop with an if statement and append is enough. Remove NotImplementedError.
3. Run: python team_tasks/recording_catalog.py
   If you received this file by itself, run: python recording_catalog.py
4.  Return only this file.

CAPTION / WHY YOUR PART MATTERS
The "bank" contains recordings the demo may select. "evaluation" recordings
are reserved for checking it and must stay out of that selectable list. A raga
is the musical setting; your job is simply to compare its supplied name.
Example: asking for Mohanam should keep the Mohanam bank entries, in order,
and leave out both other ragas and evaluation entries.
Before you finish, running this file raises NotImplementedError. That is
expected. Afterwards, it should print "Friend 2 checks passed...".

HANDOFF
Send back recording_catalog.py and one sentence explaining list_recordings.
If using GitHub, commit only this file on your own branch and open a PR. Leave the check function unchanged.

YOUR SMALL DATA TASK TOMORROW
See the seed/response file pairs
and their metadata. Copy the example dictionary below into RECORDINGS for each
pair, replacing EVERY example value. Use unique IDs, forward slashes in paths,
and exact supplied raga names. Do not guess notes, tonic, tala, or timestamps.
Only the main technical owner decides bank/evaluation membership.

COPYABLE CHATGPT PROMPT
"Help me finish only list_recordings in this Python file. I am a beginner.
Use a simple loop and explain each line. Only split='bank' records are allowed;
the optional raga filter must use exact equality. Return a new list and preserve
order. Keep names and checks unchanged, and add no dependencies. Leave the real
RECORDINGS list empty until I have actual metadata."

The main technical owner will validate file existence and integrate this module.
The example records used by _check are invented metadata, not real recordings.
"""

# Ishita reviewed the Ninnu Kori cuts and the three Mohanam practice pairs.
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
        "id": "mohanam_take30", "title": "Mohanam practice 1 - recording 30",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/mohanam_take30_timed_seed.wav",
        "response_path": "data/audio/mohanam_take30_timed_response.wav",
        "source_take": "standard_recording_30", "split": "bank",
    },
    {
        "id": "mohanam_take31", "title": "Mohanam practice 2 - recording 31",
        "raga": "Mohanam", "tala": "Adi",
        "seed_path": "data/audio/mohanam_take31_timed_seed.wav",
        "response_path": "data/audio/mohanam_take31_timed_response.wav",
        "source_take": "standard_recording_31", "split": "bank",
    },
    {
        "id": "mohanam_take32", "title": "Mohanam practice 3 - recording 32",
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
#     "split": "bank",  # or "evaluation", as assigned by the technical owner
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
    """Run after your edits. These examples do not need audio files."""
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
    print("Friend 2 checks passed. Real recording metadata can be added tomorrow.")


if __name__ == "__main__":
    _check()