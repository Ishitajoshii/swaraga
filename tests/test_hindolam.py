"""Hindolam source isolation, audio integrity, review gating and HTTP checks."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import threading
from urllib.error import HTTPError
from urllib.request import urlopen
import wave

import numpy as np
import pytest

from swaraga.audio import RATE, read_audio
from swaraga.hindolam import generate_examples
from swaraga.knowledge import SCALES, extract_composition, load_knowledge
from swaraga.recordings import RecordingBank

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / "data/audio/hindolam_review"


def review_data():
    return json.loads((FOLDER / "review.json").read_text(encoding="utf-8"))


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def test_hindolam_extractor_resolves_its_own_variants_and_rejects_foreign_notes():
    raw = b"<p>Pallavi:</p><p>S g M d N ||</p><p>S R G M P ||</p>"
    source = {"id": "test", "raga": "Hindolam", "encoding": "ascii", "sha256": hashlib.sha256(raw).hexdigest()}
    result = extract_composition(raw, source)
    assert result["passages"][0]["pitch_classes"] == list(SCALES["Hindolam"])
    assert len(result["passages"]) == 1
    assert result["excluded"][0]["reason"] == "empty or foreign swara"
    assert load_knowledge(ROOT, "Hindolam")[0]["raga"] == "Hindolam"
    assert all(c["raga"] == "Mohanam" for c in load_knowledge(ROOT))


def test_generated_hindolam_is_repeatable_in_raga_and_has_bounded_repeats():
    first = generate_examples(ROOT)
    assert first == generate_examples(ROOT)
    assert len(first) == 3
    for item in first:
        assert len(item["seed"]) == 16 and len(item["response"]) == 8
        assert not item["approved"]
        notes = item["seed"] + item["response"]
        assert all(note.rstrip("'.") in SCALES["Hindolam"] for note in notes)
        assert all(len(set(notes[i - 2:i + 1])) > 1 for i in range(16, 24))


def test_review_audio_has_valid_hashes_levels_and_contiguous_halves():
    data = review_data()
    assert not data["approved"] and len(data["items"]) == 6
    for item in data["items"]:
        assert not item["approved"] and item["split"] == "review_only"
        frames = {}
        for part, relative in item["paths"].items():
            path = FOLDER / relative
            if not path.exists():
                pytest.skip("Review WAVs are generated artifacts; run preparation first")
            content = path.read_bytes()
            assert hashlib.sha256(content).hexdigest() == item["sha256"][part]
            with wave.open(io.BytesIO(content)) as reader:
                assert reader.getnchannels() == 1 and reader.getsampwidth() == 2 and reader.getframerate() == RATE
                frames[part] = reader.readframes(reader.getnframes())
            samples = read_audio(path)
            assert np.max(np.abs(samples)) <= .851
            assert np.sqrt(np.mean(samples ** 2)) > .005
        assert frames["combined"] == frames["seed"] + frames["response"]
        if item["kind"] == "vocal":
            a, b, c = item["source_seconds"]
            assert 0 < a < b < c < data["source"]["duration_seconds"]
            assert item["join_sample_jump"] < .02
            assert "seed_events" not in item and "seed_beat_map" not in item


def test_pending_recordings_are_not_promoted_to_approved_bank():
    bank = RecordingBank(ROOT)
    assert not bank.errors
    assert not any(r["raga"] == "Hindolam" for r in bank.records)
    assert len({i["group_id"] for i in review_data()["items"] if i["kind"] == "vocal"}) == 1
    vocals = [i for i in review_data()["items"] if i["kind"] == "vocal"]
    assert all(i["review_status"] == "rejected" and i["swara_only_verified"] is False for i in vocals)


def test_quiet_cut_stays_within_requested_region():
    prepare = module("prepare_hindolam_review")
    samples = np.ones(RATE * 10) * .3
    samples[round(4.5 * RATE):round(4.6 * RATE)] = 0
    boundary = prepare.quiet_boundary(samples, 5)
    assert 4.5 <= boundary / RATE < 4.6
    with pytest.raises(ValueError, match="outside"):
        prepare.quiet_boundary(samples, 0)


@pytest.mark.parametrize("frequency", [100, 196, 329.63])
def test_pitch_diagnostic_on_known_tones(frequency):
    prepare = module("prepare_hindolam_review")
    t = np.arange(RATE) / RATE
    track, diagnostic = prepare.pitch_analysis(.2 * np.sin(2 * np.pi * frequency * t))
    assert diagnostic["confident_fraction"] > .95
    assert abs(1200 * np.log2(np.median(track[:, 1]) / frequency)) < 6


def test_review_routes_serve_expected_assets_and_reject_traversal():
    server = module("run_demo").create_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}/review/hindolam/"
    try:
        assert b"Explore Hindolam" in urlopen(base).read()
        assert b"localStorage" in urlopen(base + "review.js").read()
        assert len(json.load(urlopen(base + "review.json"))["items"]) == 6
        rejected = [f"vocal-{n}-{part}.wav" for n in range(1, 4) for part in ("seed", "response", "combined")]
        for bad in ["../../README.md", "%2e%2e%2fREADME.md", "vocal-4-combined.wav", "samajavaragamana.mp3", *rejected]:
            with pytest.raises(HTTPError) as error:
                urlopen(base + bad)
            assert error.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
