"""Source boundaries, pitch semantics, corruption checks and demo integration."""
import copy
import hashlib
import json
from pathlib import Path
import shutil

import pytest

from swaraga.demo import DemoService
from swaraga.knowledge import DATA_PATH, NotationPrior, extract_composition, load_knowledge
from swaraga.models.baseline_ngram import VariableOrderMarkov

ROOT = Path(__file__).resolve().parents[1]


def extract(text):
    raw = text.encode("cp1252")
    source = {"id": "fixture", "sha256": hashlib.sha256(raw).hexdigest(), "encoding": "cp1252"}
    return extract_composition(raw, source)


def test_notation_extraction_preserves_cues_without_fabricating_timing_or_octaves():
    composition = extract("<p>Pallavi:</p><p>G p - g R - S <u>SD</u> - S ; R | G ; ; ; ||</p>"
                          "<p>rAma ninu nammina</p><p>S R M G P D ||</p>"
                          "<p>G p - g R - S <u>SD</u> - S ; R | G ; ; ; ||</p>")
    assert len(composition["passages"]) == 1
    passage = composition["passages"][0]
    assert passage["pitch_classes"] == ["G3", "P", "G3", "R2", "S", "S", "D2", "S", "R2", "G3"]
    assert {s["text"] for s in passage["source_spans"] if s["underlined"]} == {"SD"}
    assert passage["source_paragraph"] == 1
    assert {x["reason"] for x in composition["excluded"]} == {"empty or foreign swara", "duplicate pitch-class sequence"}


def test_changed_source_requires_review():
    with pytest.raises(ValueError, match="Source changed"):
        extract_composition(b"<p>S R G P D ||</p>", {"id": "fixture", "sha256": "wrong"})


def test_caranam_spelling_is_a_section_boundary():
    composition = extract("<p>Anupallavi:</p><p>S R G P D ||</p>"
                          "<p>caraNam</p><p>D P G R S ||</p>")
    assert [p["section"] for p in composition["passages"]] == ["anupallavi", "charanam"]


def test_phrase_training_does_not_join_variations_or_inflate_counts():
    model = VariableOrderMarkov().fit_sequences([[0, 1, 2], [3, 4, 0]])
    assert dict(model.counts[1][(2,)]) == {}  # no fabricated G -> P across lines
    assert dict(model.counts[0][()]) == {0: 2, 1: 1, 2: 1, 3: 1, 4: 1}


def test_prior_changes_pitch_preferences_and_preserves_register_support():
    baseline = VariableOrderMarkov().fit_sequences([[0, 1], [0, 2], [0, 6]])
    compositions = [{"passages": [{"pitch_classes": ["S", "R2", "S", "R2", "S", "R2"]}]}]
    model = NotationPrior(baseline, compositions)
    before, after = baseline.next_scores([0]), model.next_scores([0])
    assert set(after) == set(before)
    assert after[1] / after[2] > before[1] / before[2]
    assert after[1] / after[6] == pytest.approx(before[1] / before[6])
    assert model.next_scores([5]) != baseline.next_scores([5])
    assert NotationPrior(baseline, compositions, strength=0).next_scores([0]) == before


@pytest.mark.parametrize("corruption", ["split", "foreign_note", "duplicate_group"])
def test_loader_rejects_invalid_training_data(tmp_path, corruption):
    data = json.loads((ROOT / DATA_PATH).read_text(encoding="utf-8"))
    if corruption == "split":
        data["compositions"][0]["split"] = "test"
    elif corruption == "foreign_note":
        data["compositions"][0]["passages"][0]["pitch_classes"][0] = "N3"
    else:
        data["compositions"].append(copy.deepcopy(data["compositions"][0]))
    destination = tmp_path / DATA_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_knowledge(tmp_path)


def test_real_sources_are_traceable_and_absent_from_existing_holdouts():
    compositions = load_knowledge(ROOT)
    assert len(compositions) == 2
    holdouts = [json.loads(line) for split in ("val", "test")
                for line in (ROOT / f"data/splits/{split}.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for composition in compositions:
        assert len(composition["sha256"]) == 64
        assert composition["id"] not in {r["id"] for r in holdouts}
        assert composition["title"].casefold() not in {r["title"].casefold() for r in holdouts}
        for passage in composition["passages"]:
            assert passage["section"] in {"pallavi", "anupallavi", "charanam", "charanam 1"}
            assert passage["source_spans"]


def test_demo_consumes_supplement_and_remains_reproducible(tmp_path):
    for relative in ("data/processed/normalized_dataset.parquet", "data/splits/train.jsonl",
                     "team_tasks/demo_copy.py", "team_tasks/recording_catalog.py"):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / relative, destination)
    before = DemoService(tmp_path)
    destination = tmp_path / DATA_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / DATA_PATH, destination)
    after, repeated = DemoService(tmp_path), DemoService(tmp_path)
    assert after.knowledge["compositions"] == 2
    assert after.knowledge["note_attacks"] > 1000
    assert after.training_count == before.training_count
    assert after.symbolic == repeated.symbolic
    assert any(after.symbolic[key]["generated"] != before.symbolic[key]["generated"] for key in before.symbolic)
    assert all(len(example["generated"]) == 8 for example in after.symbolic.values())
