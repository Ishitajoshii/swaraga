"""Create a local source/audio snapshot; no upload, Git mutation, or credentials."""
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["src", "demo", "scripts", "tests", "config", "data/raw", "data/interim", "data/processed", "data/splits",
           "data/audio", "data/knowledge", "team_tasks", "docs/RECORDINGS.md", "docs/MOHANAM_KNOWLEDGE.md",
           "docs/HINDOLAM_REVIEW.md", "reports", "README.md",
           "requirements.txt", "pyproject.toml", "train-00000-of-00001.parquet", ".gitignore"]


# Local-only notes must not leak into shareable source/audio snapshots.
LOCAL_NOTES = ('PRD.md', 'SUBMISSION_TODO.md', 'docs/DEMO_RUNSHEET.md', 'docs/SUBMISSION_NOTES.md', 'reports/pre_recording_verification.md')


def package():
    destination = ROOT / ".demo-artifacts"
    destination.mkdir(exist_ok=True)
    # Refresh backups and fail before packaging an invalid demo.
    import subprocess
    import sys
    subprocess.run([sys.executable, str(ROOT / "scripts/check_demo.py")], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    path = destination / ("swaraga-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".zip")
    with ZipFile(path, "x", ZIP_DEFLATED) as archive:
        for name in INCLUDE:
            base = ROOT / name
            files = sorted(base.rglob("*")) if base.is_dir() else [base]
            for file in files:
                if file.relative_to(ROOT).as_posix() in LOCAL_NOTES:
                    continue
                if file.is_file() and "__pycache__" not in file.parts and file.suffix not in (".pyc", ".pyo"):
                    if file.resolve().is_relative_to(ROOT):
                        archive.write(file, file.relative_to(ROOT))
        import json
        check = json.loads((destination / "check.json").read_text(encoding="utf-8"))
        archive.write(destination / "check.json", "backup_audio/check.json")
        for item in check["exports"]:
            archive.write(destination / "audio-backups" / item["file"], "backup_audio/" + item["file"])
        archive.writestr("SNAPSHOT_README.txt", "Mohanam demo snapshot. Read README.md for setup, playback, and reproduction instructions. backup_audio contains complete generated, prepared and retrieved phrases plus SHA-256 hashes. Python and dependencies must already be installed for offline app use; WAVs play independently. Files in data/audio, including source MP3s, are included. Hindolam vocal cuts are rejected archive artifacts, not showcase material. The recordings_originals folder and any external demo video are not included; keep separate backups of those.\n")
    print(path)
    return path


if __name__ == "__main__":
    package()
