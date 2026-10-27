"""Rebuild the source-attributed Mohanam pitch-class supplement, offline.

Supply a directory containing the two HTML files listed in sources.json.
Checksums pin the reviewed source versions; changed pages require review.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.knowledge import DATA_PATH, extract_composition, load_knowledge


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "data/knowledge/sources.json").read_text(encoding="utf-8"))
    compositions = [extract_composition((args.source_dir / source["file"]).read_bytes(), source)
                    for source in manifest["sources"]]
    data = {"schema_version": 1, "compositions": compositions}
    path = ROOT / DATA_PATH
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    load_knowledge(ROOT)
    summary = {
        "compositions": len(compositions),
        "passages": sum(len(c["passages"]) for c in compositions),
        "note_attacks": sum(len(p["pitch_classes"]) for c in compositions for p in c["passages"]),
        "by_composition": [{"id": c["id"], "passages": len(c["passages"]),
                            "note_attacks": sum(len(p["pitch_classes"]) for p in c["passages"]),
                            "excluded": c["excluded"]} for c in compositions],
        "scope": "Pitch-class order only; no inferred octaves, rhythm targets, lyrics or voice synthesis.",
        "evaluation": "Training-only addition. No held-out quality improvement claimed.",
    }
    (ROOT / "reports/mohanam_knowledge.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
