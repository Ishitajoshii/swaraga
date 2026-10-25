"""Create a local source/audio snapshot; no upload, Git mutation, or credentials."""
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = ["src", "demo", "scripts", "tests", "config", "data/raw", "data/interim", "data/processed", "data/splits",
           "data/audio", "team_tasks", "docs", "reports", "README.md", "SUBMISSION_TODO.md",
           "PRD.md", "requirements.txt", "pyproject.toml", "train-00000-of-00001.parquet", ".gitignore"]


def package():
    destination = ROOT / ".demo-artifacts"
    destination.mkdir(exist_ok=True)
    path = destination / ("swaraga-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".zip")
    with ZipFile(path, "x", ZIP_DEFLATED) as archive:
        for name in INCLUDE:
            base = ROOT / name
            files = sorted(base.rglob("*")) if base.is_dir() else [base]
            for file in files:
                if file.is_file() and "__pycache__" not in file.parts and file.suffix not in (".pyc", ".pyo"):
                    if file.resolve().is_relative_to(ROOT):
                        archive.write(file, file.relative_to(ROOT))
        archive.writestr("SNAPSHOT_README.txt", "Local demo snapshot. Read README.md for startup. Python and dependencies must already be installed for offline use. Original recordings and demo video are backed up separately. See SUBMISSION_TODO.md for incomplete tasks.\n")
    print(path)
    return path


if __name__ == "__main__":
    package()
