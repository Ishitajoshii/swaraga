"""Trim a recorded pair without changing the original. See docs/RECORDINGS.md."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from swaraga.audio import trim_take

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--id", required=True)
    parser.add_argument("--start", type=float, default=0)
    parser.add_argument("--split", type=float, required=True)
    parser.add_argument("--end", type=float, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "data/audio")
    args = parser.parse_args()
    try:
        print(json.dumps(trim_take(args.source, args.output, args.id, args.start, args.split, args.end), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
