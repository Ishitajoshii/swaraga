"""Validate every demo audio path and export complete-phrase backup WAVs."""
import argparse
import hashlib
import io
import json
import platform
from importlib.metadata import version
from pathlib import Path
import sys
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.demo import DemoService
from swaraga.audio import RATE


def check_audio(service, output):
    """Exercise every selectable combination; preserve complete phrases as backups."""
    output.mkdir(parents=True, exist_ok=True)
    cases = [("symbolic", key, "prepared", None) for key in service.symbolic]
    cases += [("vocal", r["id"], "prepared", None) for r in service.bank.records if r["split"] == "bank"]
    cases += [("vocal", r["id"], "retrieval", candidate["id"])
              for r in service.bank.records for candidate in service.bank.rank(r["id"])]
    exports = []
    for kind, key, mode, response in cases:
        frames, durations = {}, {}
        for part in ("seed", "response", "combined"):
            content = service.audio(kind, key, part, mode, response)
            with wave.open(io.BytesIO(content)) as reader:
                if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate()) != (1, 2, RATE):
                    raise ValueError(f"Unexpected audio format: {key}/{part}")
                frames[part] = reader.readframes(reader.getnframes())
                durations[part] = reader.getnframes() / RATE
            samples = np.frombuffer(frames[part], dtype="<i2").astype(float) / 32768
            if not len(samples) or np.max(np.abs(samples)) >= 1 or np.sqrt(np.mean(samples ** 2)) < .001:
                raise ValueError(f"Empty, silent or full-scale audio: {key}/{part}")
        if frames["combined"] != frames["seed"] + frames["response"]:
            raise ValueError(f"Complete phrase differs from its halves: {key}/{response}")
        filename = f"{kind}-{mode}-{key}" + (f"-to-{response}" if response else "") + ".wav"
        (output / filename).write_bytes(content)
        exports.append({"file": filename, "kind": kind, "mode": mode, "seed_id": key,
                        "response_id": response or key, "seconds": durations["combined"],
                        "sha256": hashlib.sha256(content).hexdigest()})
    return exports


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / ".demo-artifacts")
    args = parser.parse_args()
    service = DemoService(ROOT)
    state = service.state()
    args.output.mkdir(parents=True, exist_ok=True)
    for key in service.symbolic:
        (args.output / f"symbolic-{key}.wav").write_bytes(service.audio("symbolic", key, "combined"))
    exports = check_audio(service, args.output / "audio-backups")
    summary = {"symbolic_examples": len(state["symbolic"]), "recorded_pairs": len(state["recordings"]),
               "source_takes": len({r["source_take"] for r in state["recordings"]}),
               "retrieval_combinations": sum(e["mode"] == "retrieval" for e in exports),
               "audio_paths_checked": len(exports) * 3, "exports": exports,
               "runtime": {"python": platform.python_version(), **{name: version(name) for name in ("numpy", "pandas", "pyarrow")}},
               "training": state["training"], "friend_tasks": state["team"], "warnings": state["warnings"],
               "note": "Symbolic exports are synthesized; vocal exports use existing approved recordings. Checks verify audio integrity, not new musical approval."}
    (args.output / "check.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    sys.exit(1 if state["warnings"] or len(state["symbolic"]) != 3 else 0)
