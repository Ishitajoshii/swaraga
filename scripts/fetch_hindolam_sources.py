"""Fetch the public sources used by the Hindolam review, into a local cache.

Only data are downloaded; upstream Python/notebook code is never executed.
"""
from pathlib import Path
from urllib.request import Request, urlopen
import argparse
import hashlib
import io
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".demo-artifacts/hindolam-sources"
SOURCES = {
    "saraga-metadata.zip": "https://codeload.github.com/MTG/saraga/zip/refs/heads/master",
    "samajavaragamana.html": "https://www.shivkumar.org/music/samajavaragamana.htm",
}
ARCHIVE_URL = "https://zenodo.org/api/records/4301737/files/saraga1.5_carnatic.zip/content"
TRACK = "Chaitra Sairam at Arkay by Chaitra Sairam/Govardhana Girisham/Govardhana Girisham"


class RemoteArchive(io.RawIOBase):
    """Read only requested ZIP ranges; refuse a server that sends the full archive."""
    def __init__(self, url):
        self.url = url
        self.position = 0
        self.size = None
        self.transferred = 0
        self._range(0, 0)

    def _range(self, start, end):
        request = Request(self.url, headers={"User-Agent": "Mozilla/5.0", "Range": f"bytes={start}-{end}"})
        with urlopen(request, timeout=60) as response:
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if response.status != 206 or not match or (int(match[1]), int(match[2])) != (start, end):
                raise ValueError("Server did not honor the requested byte range; full archive not downloaded")
            self.size = int(match[3])
            data = response.read(end - start + 2)
        if len(data) != end - start + 1:
            raise ValueError("Incomplete archive range")
        self.transferred += len(data)
        return data

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if not 0 <= self.position <= self.size:
            raise ValueError("Invalid archive seek")
        return self.position

    def tell(self):
        return self.position

    def read(self, size=-1):
        size = self.size - self.position if size < 0 else min(size, self.size - self.position)
        if size > 40_000_000:
            raise ValueError("Requested ZIP member exceeds download limit")
        if not size:
            return b""
        data = self._range(self.position, self.position + size - 1)
        self.position += size
        return data


def fetch_audio():
    local = zipfile.ZipFile(CACHE / "saraga-metadata.zip")
    prefix = "saraga-master/dataset/carnatic/" + TRACK
    metadata = json.loads(local.read(prefix + ".json"))
    if [r["common_name"] for r in metadata["raaga"]] != ["hindolam"]:
        raise ValueError("Source is not exclusively Hindolam")
    for extension in ("json", "ctonic.txt", "sama-manual.txt"):
        (CACHE / ("govardhana." + extension)).write_bytes(local.read(prefix + "." + extension))
    (CACHE / "saraga-license.txt").write_bytes(local.read("saraga-master/LICENSE.md"))
    pending = []
    for extension in ("mp3", "pitch"):
        expected = local.read(prefix + "." + extension + ".md5").decode().strip().split()[0]
        path = CACHE / ("govardhana." + ("mp3" if extension == "mp3" else "pitch.txt"))
        if path.exists() and hashlib.md5(path.read_bytes()).hexdigest() == expected:
            print(f"Verified cached {path.name}", flush=True)
        else:
            pending.append((extension, expected, path))
    if not pending:
        return
    remote = RemoteArchive(ARCHIVE_URL)
    with zipfile.ZipFile(remote) as archive:
        for extension, expected, path in pending:
            suffix = TRACK + (".mp3.mp3" if extension == "mp3" else ".pitch.txt")
            matches = [n for n in archive.namelist() if n.endswith(suffix)]
            if len(matches) != 1:
                raise ValueError(f"Expected one archive member: {suffix}; found {matches}")
            member = archive.getinfo(matches[0])
            if member.file_size > 40_000_000:
                raise ValueError("Source exceeds download limit")
            data = archive.read(member)
            if hashlib.md5(data).hexdigest() != expected:
                raise ValueError("Audio/pitch checksum disagrees with upstream metadata")
            path.write_bytes(data)
            print(f"Downloaded and checksum-verified {path.name}: {len(data):,} bytes", flush=True)
    print(f"Fetched {remote.transferred:,} bytes from the {remote.size:,}-byte archive", flush=True)


def fetch(url, limit=40_000_000):
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=45) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Download exceeds the expected size limit")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", action="store_true", help="fetch only the selected Hindolam recording and pitch data")
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        path = CACHE / name
        if not path.exists():
            path.write_bytes(fetch(url))
        print(f"{name}: {path.stat().st_size:,} bytes", flush=True)
    if args.audio:
        fetch_audio()


if __name__ == "__main__":
    main()
