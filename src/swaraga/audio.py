"""Local PCM audio tools. Originals are never modified; no network services."""
from __future__ import annotations

import io
import math
from pathlib import Path
import shutil
import subprocess
import wave

import numpy as np

RATE = 24000
SEMITONES = {"S": 0, "R1": 1, "R2": 2, "R3": 3, "G1": 2, "G2": 3,
             "G3": 4, "M1": 5, "M2": 6, "P": 7, "D1": 8, "D2": 9,
             "D3": 10, "N1": 9, "N2": 10, "N3": 11}


def read_audio(path: Path) -> np.ndarray:
    """Decode to mono float samples at 24 kHz. M4A/MP3 require local FFmpeg."""
    path = Path(path)
    if path.suffix.lower() != ".wav":
        executable = shutil.which("ffmpeg")
        if not executable:
            raise ValueError("M4A/MP3 conversion needs FFmpeg on PATH; supply a PCM WAV for now.")
        result = subprocess.run(
            [executable, "-v", "error", "-i", str(path), "-t", "601", "-f", "wav",
             "-acodec", "pcm_s16le", "-ac", "1", "-ar", str(RATE), "pipe:1"],
            capture_output=True, check=True, timeout=90)
        source = io.BytesIO(result.stdout)
    else:
        source = str(path)
    try:
        with wave.open(source, "rb") as recording:
            width, channels, rate = recording.getsampwidth(), recording.getnchannels(), recording.getframerate()
            if width not in (1, 2, 3, 4) or recording.getcomptype() != "NONE":
                raise ValueError("Use an uncompressed PCM WAV.")
            if recording.getnframes() / rate > 600 and isinstance(source, str):
                raise ValueError("Please split source recordings longer than 10 minutes first.")
            raw = recording.readframes(rate * 601)
    except (wave.Error, EOFError) as exc:
        raise ValueError("Audio is not a readable PCM WAV; convert it to PCM WAV first.") from exc
    if width == 1:
        samples = (np.frombuffer(raw, dtype=np.uint8).astype(float) - 128) / 128
    elif width == 3:
        chunks = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        values = chunks[:, 0] | (chunks[:, 1] << 8) | (chunks[:, 2] << 16)
        samples = ((values ^ 0x800000) - 0x800000) / 8388608.0
    else:
        samples = np.frombuffer(raw, dtype="<i" + str(width)).astype(float) / (2 ** (8 * width - 1))
    samples = samples.reshape(-1, channels).mean(axis=1)
    if len(samples) / rate > 600:
        raise ValueError("Please split source recordings longer than 10 minutes first.")
    if not len(samples):
        raise ValueError("Recording is empty.")
    if rate != RATE:
        count = round(len(samples) * RATE / rate)
        samples = np.interp(np.arange(count) * rate / RATE, np.arange(len(samples)), samples)
    return samples


def wav_bytes(samples: np.ndarray) -> bytes:
    """Attenuate only if necessary; do not boost noise or normalize each phrase."""
    samples = np.asarray(samples, dtype=float)
    if samples.ndim != 1 or not np.isfinite(samples).all():
        raise ValueError("Expected finite mono audio samples.")
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    if peak > 0.95:
        samples = samples * (0.95 / peak)
    output = io.BytesIO()
    with wave.open(output, "wb") as recording:
        recording.setnchannels(1)
        recording.setsampwidth(2)
        recording.setframerate(RATE)
        recording.writeframes((samples * 32767).astype("<i2").tobytes())
    return output.getvalue()


def trim_take(source: Path, output_dir: Path, clip_id: str, start: float,
              split: float, end: float) -> dict:
    """Export seed/response copies, refusing overwrite, and save cut provenance."""
    import json
    import re
    if not re.fullmatch(r"[a-zA-Z0-9_-]+", clip_id):
        raise ValueError("Clip ID must contain only letters, digits, underscores or hyphens.")
    samples = read_audio(source)
    if not all(math.isfinite(v) for v in (start, split, end)) or not 0 <= start < split < end <= len(samples) / RATE:
        raise ValueError("Require 0 <= start < split < end <= recording duration.")
    output_dir = Path(output_dir)
    paths = [output_dir / f"{clip_id}_{part}.wav" for part in ("seed", "response")]
    provenance = output_dir / f"{clip_id}_cuts.json"
    if any(p.exists() for p in [*paths, provenance]):
        raise ValueError("Output already exists; choose a new clip ID to preserve prior work.")
    output_dir.mkdir(parents=True, exist_ok=True)
    # Use one gain for the pair so its relative loudness is preserved.
    peak = float(np.max(np.abs(samples)))
    samples = samples * min(1.0, 0.95 / max(peak, 1e-12))
    for path, a, b in zip(paths, (start, split), (split, end)):
        path.write_bytes(wav_bytes(samples[round(a * RATE):round(b * RATE)]))
    info = {"source": str(Path(source).resolve()), "start": start, "split": split,
            "end": end, "peak_before": peak, "possible_clipping": peak >= 0.999,
            "sample_rate": RATE, "seed_path": str(paths[0]), "response_path": str(paths[1])}
    provenance.write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def synthesize(tokens: list[str], tonic_hz: float = 240, seconds: float = 0.32) -> np.ndarray:
    """Plain equal-tempered reference tones; no vocal synthesis or gamakas."""
    chunks = []
    for token in tokens:
        t = np.arange(round(seconds * RATE)) / RATE
        if token == "[REST]":
            chunks.append(np.zeros(len(t)))
            continue
        base = token.rstrip("'.")
        semitone = SEMITONES[base] + 12 * (token.count("'") - token.count("."))
        frequency = tonic_hz * 2 ** (semitone / 12)
        envelope = np.minimum(1, t / 0.012) * np.minimum(1, (seconds - t) / 0.035)
        tone = (np.sin(2 * np.pi * frequency * t) + 0.22 * np.sin(4 * np.pi * frequency * t))
        chunks.append(0.24 * envelope * tone)
    return np.concatenate(chunks) if chunks else np.zeros(0)
