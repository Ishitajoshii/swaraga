"""Validate the local demo and export reproducible synthesized backup WAVs."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.demo import DemoService


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".demo-artifacts")
    args = parser.parse_args()
    service = DemoService(ROOT)
    state = service.state()
    args.output.mkdir(parents=True, exist_ok=True)
    for key in service.symbolic:
        (args.output / f"symbolic-{key}.wav").write_bytes(service.audio("symbolic", key, "combined"))
    summary = {"symbolic_examples": len(state["symbolic"]), "recorded_pairs": len(state["recordings"]),
               "training": state["training"], "friend_tasks": state["team"], "warnings": state["warnings"],
               "note": "Exported WAVs are synthesized reference tones, not voice recordings."}
    (args.output / "check.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    sys.exit(1 if state["warnings"] or len(state["symbolic"]) != 3 else 0)
