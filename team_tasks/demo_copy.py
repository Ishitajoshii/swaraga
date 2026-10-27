"""FRIEND 1: friendly text for the Swaraga demo (about 30–45 minutes).

You only need this file and Python. Do not install anything or edit other files.
Use Python 3.10 or newer. If Python is not installed, just return the edited
file and put up a pull request; you do not need to set up the whole repo.

YOUR SMALL CODING TASK
1. Replace the three strings marked TODO in TEXT with clear, short wording.
2. Complete get_text(key): return the value for key if it is in TEXT, otherwise
   return TEXT["unknown"]. This is a dictionary lookup with a fallback.
3. Remove the NotImplementedError after writing the function.
4. Run: python team_tasks/demo_copy.py
   If you received this file by itself, run: python demo_copy.py

CAPTION / WHY YOUR PART MATTERS
These captions explain the demo to the audience. The fallback keeps an unknown
label request from breaking the screen. Your change is only this one file.
Before you finish, running the file will report an AssertionError about TODO
text or a NotImplementedError. That is expected: it marks the work left for you.
After you finish, it should print "Friend 1 checks passed...".

HANDOFF
Send back demo_copy.py and one sentence explaining get_text. If using GitHub,
commit only this file on your own branch and open a PR.
Do not paste your answer into a different file or remove the check function.

COPYABLE CHATGPT PROMPT
"Help me complete only the TODOs in this Python file. I am a beginner. Explain
dictionary lookup and a fallback in simple terms. Keep all dictionary keys and
function names unchanged. Do not add packages or change the checks. The product
selects recorded vocal phrases and separately generates symbolic swaras. Do not
claim it clones a voice or sings any arbitrary generated notes."

This is UI wording, not a claim that the demo has already been implemented.
The main technical owner will import this file when integrating the UI.
"""

TEXT = {
    "title": "Swaraga",
    "subtitle": (
        "Explore short Carnatic phrases through recorded vocal responses "
        "and separately generated swaras."
    ),
    "seed_label": "Your recorded seed phrase",
    "vocal_mode": "Recorded vocal response",
    "symbolic_mode": "Generated swaras",
    "play_seed": "Play seed",
    "play_response": "Play response",
    "empty_catalog": (
        "No recordings have been added yet, so the recorded vocal response "
        "is not available."
    ),
    "vocal_explanation": (
        "This mode selects a compatible recorded phrase in the singer's voice."
    ),
    "symbolic_explanation": (
        "This mode generates swaras. Instrumental playback is synthesized."
    ),
    "limitations": (
        "This demo currently supports only a small curated bank of phrases."
    ),
    "unknown": "Information unavailable",
}


def get_text(key: str) -> str:
    """Return the requested UI text, or the 'unknown' text for an unknown key."""
    return TEXT.get(key, TEXT["unknown"])


def _check() -> None:
    """Run this after your edits. Leave the checks unchanged."""
    assert all(isinstance(value, str) and value.strip() for value in TEXT.values())
    assert not any("TODO" in value for value in TEXT.values()), "Finish the three text TODOs."
    assert get_text("title") == "Swaraga"
    assert get_text("play_seed") == TEXT["play_seed"]
    assert get_text("missing_key") == TEXT["unknown"]
    print("Friend 1 checks passed. Ask agent to review the wording, then return this file.")


if __name__ == "__main__":
    _check()
