"""Interface text and fallback lookup for Swaraga."""

TEXT = {
    'title': 'Swaraga',
    'subtitle': 'Explore Carnatic melodies. Generate a continuation, discover vocal phrases, and hear how the music unfolds.',
    'seed_label': 'Opening phrase',
    'vocal_mode': 'Vocal library',
    'symbolic_mode': 'Generate swaras',
    'play_seed': 'Play opening phrase',
    'play_response': 'Play continuation',
    'empty_catalog': 'No vocal recordings are available in this installation. Add recordings using the recording guide in the README.',
    'vocal_explanation': 'Listen to an original phrase pair or find a compatible continuation from the library.',
    'symbolic_explanation': 'Choose an opening phrase and explore its eight-note continuation with instrumental playback.',
    'limitations': 'Vocal phrases are recorded performances. Matching selects an existing response; it does not synthesize a voice.',
    'unknown': 'Information unavailable',
}


def get_text(key: str) -> str:
    """Return the requested UI text, or the 'unknown' text for an unknown key."""
    return TEXT.get(key, TEXT["unknown"])


def _check() -> None:
    """Validate interface text and fallback behavior."""
    assert all(isinstance(value, str) and value.strip() for value in TEXT.values())
    assert not any("TODO" in value for value in TEXT.values()), "Interface text must not contain placeholders."
    assert get_text("title") == "Swaraga"
    assert get_text("play_seed") == TEXT["play_seed"]
    assert get_text("missing_key") == TEXT["unknown"]


if __name__ == "__main__":
    _check()
    print("Interface text checks passed.")
