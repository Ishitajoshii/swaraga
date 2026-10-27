"""Pre-recording checks use generated tones, never fabricated vocal recordings."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import threading
from urllib.error import HTTPError
from urllib.request import urlopen
import wave

import numpy as np
import pytest

from swaraga.audio import RATE, read_audio, synthesize, trim_take, wav_bytes
from swaraga.demo import DemoService
from swaraga.recordings import RecordingBank, audio_path, beat_offset, validate_annotation

ROOT = Path(__file__).resolve().parents[1]


def test_articulated_reference_notes_have_separate_attacks_and_same_duration():
    audio = synthesize(["S", "S", "[REST]", "R2"], articulated=True)
    length = round(.32 * RATE)
    assert len(audio) == 4 * length
    for index in (0, 1, 3):
        note = audio[index * length:(index + 1) * length]
        assert np.max(np.abs(note[:length // 3])) > .05
        assert np.all(note[round(.91 * length):] == 0)
    assert np.all(audio[2 * length:3 * length] == 0)


def annotation(group):
    event = {"kind": "note", "swara": "S", "octave": 0, "onset": 0, "duration": 1, "cycle_position": 0}
    return {"approved": True, "group_id": group, "tonic_hz": 240, "tempo_bpm": 60,
            "beats_per_cycle": 8, "seed_start_beat": 0, "response_start_beat": 1,
            "seed_events": [event], "response_events": [{**event, "cycle_position": 1}]}


@pytest.fixture
def empty_root(tmp_path):
    (tmp_path / "team_tasks").mkdir()
    (tmp_path / "data/audio").mkdir(parents=True)
    (tmp_path / "team_tasks/recording_catalog.py").write_text(
        "RECORDINGS = []\ndef _check():\n    raise NotImplementedError('fixture')\n", encoding="utf-8")
    (tmp_path / "team_tasks/demo_copy.py").write_text(
        "def _check():\n    raise NotImplementedError('fixture')\n", encoding="utf-8")
    (tmp_path / "data/audio/annotations.json").write_text("{}", encoding="utf-8")
    return tmp_path


@pytest.fixture
def bank_root(empty_root):
    tmp_path = empty_root
    records, annotations = [], {}
    for key, split, group in [("a", "bank", "one"), ("b", "bank", "two"), ("c", "evaluation", "three")]:
        for part in ("seed", "response"):
            (tmp_path / f"data/audio/{key}_{part}.wav").write_bytes(wav_bytes(synthesize(["S"], seconds=1)))
        records.append({"id": key, "title": key, "raga": "Mohanam", "tala": "Adi", "split": split,
                        "source_take": key, "seed_path": f"data/audio/{key}_seed.wav", "response_path": f"data/audio/{key}_response.wav"})
        annotations[key] = annotation(group)
    # Append fixture metadata; retain the friend's unimplemented function.
    with (tmp_path / "team_tasks/recording_catalog.py").open("a", encoding="utf-8") as handle:
        handle.write("\nRECORDINGS = " + repr(records) + "\n")
    (tmp_path / "data/audio/annotations.json").write_text(json.dumps(annotations), encoding="utf-8")
    return tmp_path


def test_three_symbolic_examples_are_repeatable_and_real_wavs(empty_root):
    for relative in ("data/processed/normalized_dataset.parquet", "data/splits/train.jsonl"):
        destination = empty_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, destination)
    first, second = DemoService(empty_root), DemoService(empty_root)
    assert len(first.symbolic) == 3
    assert first.symbolic == second.symbolic
    assert first.composition_count > 0 and first.training_count > 0
    assert first.bank.records == []
    assert not first.copy_ready and not first.bank.friend_ready
    for key, example in first.symbolic.items():
        assert len(example["tokens"]) == 16 and len(example["generated"]) == 8
        for part, positions in [("seed", 16), ("response", 8), ("combined", 24)]:
            with wave.open(io.BytesIO(first.audio("symbolic", key, part))) as audio:
                assert audio.getnchannels() == 1 and audio.getframerate() == RATE
                assert audio.getnframes() == round(0.32 * RATE) * positions


def test_trim_preserves_original_and_refuses_overwrite(tmp_path):
    source = tmp_path / "original.wav"
    original = wav_bytes(synthesize(["S", "P"], seconds=1))
    source.write_bytes(original)
    info = trim_take(source, tmp_path / "cuts", "example", 0, 1, 2)
    assert source.read_bytes() == original
    assert len(read_audio(Path(info["seed_path"]))) == RATE
    assert len(read_audio(Path(info["response_path"]))) == RATE
    with pytest.raises(ValueError, match="already exists"):
        trim_take(source, tmp_path / "cuts", "example", 0, 1, 2)
    with pytest.raises(ValueError, match="Require"):
        trim_take(source, tmp_path / "cuts", "bad", 0, 2, 1)


def test_stereo_pcm_resamples_and_levels_do_not_boost(tmp_path):
    path = tmp_path / "stereo.wav"
    with wave.open(str(path), "wb") as recording:
        recording.setnchannels(2); recording.setsampwidth(2); recording.setframerate(48000)
        recording.writeframes(np.full((48000, 2), 2000, dtype="<i2").tobytes())
    samples = read_audio(path)
    assert len(samples) == RATE
    assert np.max(samples) < 0.07
    output = tmp_path / "roundtrip.wav"
    output.write_bytes(wav_bytes(samples))
    assert np.max(read_audio(output)) < 0.07


def test_retrieval_excludes_evaluation_and_same_group(bank_root):
    bank = RecordingBank(bank_root)
    assert not bank.errors
    assert not bank.friend_ready
    assert [r["id"] for r in bank.rank("a")] == ["b"]
    assert [r["id"] for r in bank.rank("c")] == ["a", "b"]
    bank.get("b")["annotation"]["tonic_hz"] = 300
    assert bank.rank("a") == []


@pytest.mark.parametrize("field,value", [("raga", "Hindolam"), ("tala", "Rupaka")])
def test_retrieval_requires_same_musical_setting(bank_root, field, value):
    bank = RecordingBank(bank_root)
    bank.get("b")[field] = value
    assert bank.rank("a") == []


def test_tempo_and_timing_must_match(bank_root):
    bank = RecordingBank(bank_root)
    bank.get("b")["annotation"]["tempo_bpm"] = 90
    assert bank.rank("a") == []
    bank.get("b")["annotation"]["tempo_bpm"] = 60
    bank.get("b")["annotation"]["response_start_beat"] = 3
    assert bank.rank("a") == []


def test_cross_split_source_groups_block_bank(bank_root):
    path = bank_root / "data/audio/annotations.json"
    annotations = json.loads(path.read_text())
    annotations["c"]["group_id"] = "one"
    path.write_text(json.dumps(annotations))
    bank = RecordingBank(bank_root)
    assert bank.records == []
    assert "leakage" in bank.errors[-1]


def test_annotations_distinguish_holds_rests_and_reject_bad_timing():
    a = annotation("one")
    a["seed_events"] = [
        {"kind": "note", "swara": "S", "octave": 0, "onset": 0, "duration": 0.4, "cycle_position": 0},
        {"kind": "hold", "swara": "S", "octave": 0, "onset": 0.4, "duration": 0.3, "cycle_position": 0.4},
        {"kind": "rest", "swara": None, "octave": 0, "onset": 0.7, "duration": 0.3, "cycle_position": 0.7},
    ]
    validate_annotation(a, {"seed": 1, "response": 1})
    broken = copy.deepcopy(a)
    broken["seed_events"][1]["swara"] = "P"
    with pytest.raises(ValueError, match="hold"):
        validate_annotation(broken, {"seed": 1, "response": 1})
    broken = copy.deepcopy(a)
    broken["seed_events"][2]["cycle_position"] = 4
    with pytest.raises(ValueError, match="cycle_position"):
        validate_annotation(broken, {"seed": 1, "response": 1})


def test_bad_audio_path_and_invalid_annotations_are_not_selectable(bank_root):
    with pytest.raises(ValueError, match="relative"):
        audio_path(bank_root, "../outside.wav")
    (bank_root / "data/audio/annotations.json").write_text("{}")
    bank = RecordingBank(bank_root)
    assert not bank.records and len(bank.errors) == 3


def test_corrupt_recording_is_reported_without_crashing(bank_root):
    (bank_root / "data/audio/a_seed.wav").write_bytes(b"not a WAV")
    bank = RecordingBank(bank_root)
    assert [r["id"] for r in bank.records] == ["b", "c"]
    assert "readable PCM WAV" in bank.errors[0]


def test_completed_friend_modules_are_used(bank_root):
    with (bank_root / "team_tasks/demo_copy.py").open("a", encoding="utf-8") as file:
        file.write("\ndef _check():\n    pass\ndef get_text(key):\n    return 'Reviewed ' + key\n")
    with (bank_root / "team_tasks/recording_catalog.py").open("a", encoding="utf-8") as file:
        file.write("\ndef _check():\n    pass\ndef list_recordings(records, raga=None):\n    return [r for r in records if r['split'] == 'bank']\n")
    service = DemoService(bank_root)
    assert service.copy_ready and service.bank.friend_ready
    assert service.text["subtitle"] == "Reviewed subtitle"
    assert [r["id"] for r in service.bank.selectable] == ["a", "b"]


def test_vocal_playback_combines_selected_recordings_without_changing_source(bank_root):
    service = DemoService(bank_root)
    data = service.audio("vocal", "a", "combined", "retrieval", "b")
    with wave.open(io.BytesIO(data)) as audio:
        assert audio.getnframes() == 2 * RATE
    with pytest.raises(ValueError, match="constraints"):
        service.audio("vocal", "a", "combined", "retrieval", "c")
    with pytest.raises(ValueError, match="Evaluation"):
        service.audio("vocal", "c", "combined", "prepared")


def phrase_annotation(group):
    return {"approved": True, "level": "phrase", "approved_for": "prepared_playback",
            "group_id": group, "shruti_label": "G# / 5.5", "seed_notation": "G , G ,",
            "response_notation": "S R G R", "review_scope": "Singer approved phrase cuts and joins."}


def test_phrase_approval_enables_playback_but_never_retrieval(bank_root):
    path = bank_root / "data/audio/annotations.json"
    annotations = json.loads(path.read_text())
    annotations["a"] = phrase_annotation("one")
    path.write_text(json.dumps(annotations))
    service = DemoService(bank_root)
    assert service.bank.errors == []
    for part, seconds in (("seed", 1), ("response", 1), ("combined", 2)):
        with wave.open(io.BytesIO(service.audio("vocal", "a", part))) as audio:
            assert audio.getnframes() == seconds * RATE
    assert service.bank.rank("a") == []  # Phrase query cannot be ranked.
    assert service.bank.rank("b") == []  # Phrase candidate cannot be selected.
    with pytest.raises(ValueError, match="No compatible"):
        service.audio("vocal", "a", "combined", "retrieval")


def test_phrase_review_does_not_approve_note_or_tala_timing():
    a = phrase_annotation("one")
    validate_annotation(a, {"seed": 1, "response": 1})
    for field, value in (("approved", False), ("approved_for", "all"),
                         ("seed_notation", ""), ("level", "unknown"),
                         ("seed_events", []), ("tempo_bpm", 60)):
        with pytest.raises(ValueError):
            validate_annotation({**a, field: value}, {"seed": 1, "response": 1})
    with pytest.raises(ValueError):
        validate_annotation({**a, "level": "note"}, {"seed": 1, "response": 1})


def test_phrase_approval_still_enforces_source_group_isolation(bank_root):
    path = bank_root / "data/audio/annotations.json"
    annotations = json.loads(path.read_text())
    annotations["a"] = phrase_annotation("one")
    annotations["c"] = phrase_annotation("one")
    path.write_text(json.dumps(annotations))
    bank = RecordingBank(bank_root)
    assert not bank.records
    assert "leakage" in bank.errors[-1]


def mapped_annotation(group):
    a = annotation(group)
    a.update(tempo_bpm=120, response_start_beat=3,
             seed_beat_map=[{"onset": 0, "beat": 0}, {"onset": .4, "beat": 1},
                            {"onset": 1, "beat": 3}],
             response_beat_map=[{"onset": 0, "beat": 0}, {"onset": 1, "beat": 1}])
    a["response_events"][0]["cycle_position"] = 3
    return a


def test_variable_beat_map_controls_note_phase_and_retrieval_join(bank_root):
    a = mapped_annotation("one")
    a["seed_events"] = [
        {"kind": "note", "swara": "S", "octave": 0, "onset": 0, "duration": .4, "cycle_position": 0},
        {"kind": "hold", "swara": "S", "octave": 0, "onset": .4, "duration": .6, "cycle_position": 1},
    ]
    validate_annotation(a, {"seed": 1, "response": 1})
    assert beat_offset(a, "seed", .4) == 1
    assert beat_offset(a, "seed", 1) == 3
    assert beat_offset(a, "response", 1) == 1
    broken = copy.deepcopy(a)
    broken["seed_events"][1]["cycle_position"] = .8  # Constant clock is wrong here.
    with pytest.raises(ValueError, match="cycle_position"):
        validate_annotation(broken, {"seed": 1, "response": 1})
    path = bank_root / "data/audio/annotations.json"
    annotations = json.loads(path.read_text())
    annotations["a"] = a
    annotations["b"] = mapped_annotation("two")
    path.write_text(json.dumps(annotations))
    bank = RecordingBank(bank_root)
    assert not bank.errors
    assert [r["id"] for r in bank.rank("a")] == ["b"]


@pytest.mark.parametrize("anchors", [
    [], [{"onset": 0, "beat": 0}],
    [{"onset": 0, "beat": 0}, {"onset": 0, "beat": 1}],
    [{"onset": 0, "beat": 0}, {"onset": 1, "beat": 0}],
    [{"onset": .1, "beat": 0}, {"onset": 1, "beat": 1}],
    [{"onset": 0, "beat": 1}, {"onset": 1, "beat": 2}],
    [{"onset": 0, "beat": 0}, {"onset": .9, "beat": 1}],
    [{"onset": 0, "beat": 0}, {"onset": 1, "beat": 10}],
])
def test_invalid_beat_maps_are_rejected(anchors):
    a = mapped_annotation("one")
    a["seed_beat_map"] = anchors
    with pytest.raises(ValueError):
        validate_annotation(a, {"seed": 1, "response": 1})


def test_partial_beat_map_cannot_silently_use_a_constant_clock():
    a = mapped_annotation("one")
    del a["response_beat_map"]
    with pytest.raises(ValueError, match="beat map"):
        validate_annotation(a, {"seed": 1, "response": 1})


def test_shared_split_group_blocks_leakage_between_distinct_exercises(bank_root):
    path = bank_root / "data/audio/annotations.json"
    annotations = json.loads(path.read_text())
    # Distinct exercises may be retrieval candidates, but related data must
    # still remain in one split rather than becoming claimed held-out evidence.
    annotations["a"]["split_group_id"] = "practice_batch"
    annotations["c"]["split_group_id"] = "practice_batch"
    path.write_text(json.dumps(annotations))
    bank = RecordingBank(bank_root)
    assert not bank.records
    assert "leakage" in bank.errors[-1]


def test_local_http_routes_and_invalid_requests():
    spec = importlib.util.spec_from_file_location("run_demo", ROOT / "scripts/run_demo.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    server = module.create_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with pytest.raises(OSError):
            module.create_server(server.server_port)
        assert b"A phrase," in urlopen(base).read()
        assert len(json.load(urlopen(base + "/api/state"))["symbolic"]) == 3
        audio = urlopen(base + "/api/audio?kind=symbolic&id=ascent&part=combined")
        assert audio.headers["Content-Type"] == "audio/wav"
        assert audio.read()[:4] == b"RIFF"
        for route, code in [("/api/audio?kind=symbolic&id=bad&part=seed", 400), ("/../../README.md", 404)]:
            with pytest.raises(HTTPError) as error:
                urlopen(base + route)
            assert error.value.code == code
    finally:
        server.shutdown(); server.server_close(); thread.join()
