"""Source-attributed notation supplements for the local Mohanam demo.

These sources support pitch-class order, not verified octave or rhythm targets.
Never pass their case/underlines through the legacy notation parser: they have
different semantics. Each printed variation is an independent training sequence.
"""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re

from .models.baseline_ngram import VariableOrderMarkov
from .windows import is_note

SCALE = ("S", "R2", "G3", "P", "D2")
LETTERS = dict(zip("SRGPD", SCALE))
DATA_PATH = Path("data/knowledge/mohanam_notation.json")
SCALES = {"Mohanam": SCALE, "Hindolam": ("S", "G2", "M1", "D1", "N2")}


class NotationParagraphs(HTMLParser):
    """Extract paragraph text and underline spans from Word-exported HTML.

    Paragraph indexes are zero-based and include empty/source prose paragraphs,
    making each selected line locatable in the downloaded source. No scripts,
    links, prose, lyrics or HTML are executed or included as training text.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.paragraphs = []
        self.parts = None
        self.underline = 0

    def handle_starttag(self, tag, attrs):
        if tag == "p":
            self.parts = []
            self.underline = 0
        elif tag == "u" and self.parts is not None:
            self.underline += 1
        elif tag == "br" and self.parts is not None:
            self.parts.append({"text": " ", "underlined": bool(self.underline)})

    def handle_endtag(self, tag):
        if tag == "p" and self.parts is not None:
            self.paragraphs.append(self.parts)
            self.parts = None
        elif tag == "u":
            self.underline = max(0, self.underline - 1)

    def handle_data(self, data):
        if self.parts is not None:
            # HTML source newlines are whitespace; retain the visible punctuation.
            text = re.sub(r"\s+", " ", data)
            if self.parts and self.parts[-1]["underlined"] == bool(self.underline):
                self.parts[-1]["text"] += text
            else:
                self.parts.append({"text": text, "underlined": bool(self.underline)})


def extract_composition(raw: bytes, source: dict) -> dict:
    """Accept only self-contained, alphabet-checked notation paragraphs.

    Case, punctuation, barlines and underlining stay in source_spans. Only the
    explicitly written swara attacks enter pitch_classes; a comma/semicolon
    never becomes a rest or another attack. Do not infer unmarked octaves.
    """
    digest = hashlib.sha256(raw).hexdigest()
    if digest != source["sha256"]:
        raise ValueError(f"Source changed; review before importing: {source['id']}")
    parser = NotationParagraphs()
    scale = SCALES[source.get("raga", "Mohanam")]
    letters_to_swaras = {swara[0]: swara for swara in scale}
    parser.feed(raw.decode(source["encoding"], errors="replace"))
    section = None
    passages, excluded, seen = [], [], set()
    for index, spans in enumerate(parser.paragraphs):
        text = re.sub(r"\s+", " ", "".join(s["text"] for s in spans)).strip()
        header = re.fullmatch(r"(Pallavi|Anupallavi|Ch?aranam(?:\s+\d+)?)\s*:?", text, re.I)
        if header:
            section = header[1].lower().replace("caranam", "charanam")
        if section is None or "||" not in text:
            continue
        # Prose/lyrics are not notation candidates. Foreign swaras are caught
        # below rather than silently stripped from a would-be melody.
        if not re.fullmatch(r"[SRGMPDNsrgmpdn\s,;|\-–—]+", text):
            excluded.append({"paragraph": index, "reason": "unsupported notation or non-notation text"})
            continue
        letters = re.findall(r"[A-Za-z]", text)
        if not letters or any(c.upper() not in letters_to_swaras for c in letters):
            excluded.append({"paragraph": index, "reason": "empty or foreign swara"})
            continue
        if not text.endswith("||") or text.count("||") != 1:
            excluded.append({"paragraph": index, "reason": "ambiguous variation boundary"})
            continue
        pitches = [letters_to_swaras[c.upper()] for c in letters]
        # Repeated printed lines should not artificially strengthen the prior.
        key = tuple(pitches)
        if key in seen:
            excluded.append({"paragraph": index, "reason": "duplicate pitch-class sequence"})
            continue
        if len(pitches) < 5:
            excluded.append({"paragraph": index, "reason": "fewer than five attacks"})
            continue
        seen.add(key)
        passages.append({
            "id": f"{source['id']}:p{index}", "section": section,
            "source_paragraph": index, "source_spans": spans,
            "pitch_classes": pitches,
        })
    if not passages:
        raise ValueError(f"No usable notation: {source['id']}")
    return {**source, "split": "train", "group_id": source["id"],
            "representation": "pitch_class_attacks",
            "octaves": "unspecified; not inferred",
            "timing": "source punctuation and underlines retained; not validated or trained",
            "review": "source-text extraction and scale checked; no musician or listening validation",
            "passages": passages, "excluded": excluded}


def load_knowledge(root: Path, raga: str = "Mohanam") -> list[dict]:
    if raga not in SCALES:
        raise ValueError("Unsupported notation raga")
    scale = SCALES[raga]
    path = root / f"data/knowledge/{raga.lower()}_notation.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("Unsupported notation knowledge schema")
    compositions = data["compositions"]
    ids, passage_ids = set(), set()
    for composition in compositions:
        key = composition["id"]
        if key in ids or composition["group_id"] != key or composition["split"] != "train":
            raise ValueError("Notation compositions must have unique, training-only source groups")
        ids.add(key)
        if composition["raga"] != raga or composition["representation"] != "pitch_class_attacks":
            raise ValueError(f"Notation supplement must contain {raga} pitch-class attacks")
        if not composition["passages"] or not composition["url"].startswith("https://"):
            raise ValueError("Missing notation or source URL")
        for passage in composition["passages"]:
            if passage["id"] in passage_ids:
                raise ValueError("Duplicate notation passage id")
            passage_ids.add(passage["id"])
            if len(passage["pitch_classes"]) < 5 or any(p not in scale for p in passage["pitch_classes"]):
                raise ValueError(f"Invalid {raga} pitch class")
    return compositions


class NotationPrior:
    """Reweight the baseline's registered candidates using source pitch order.

    The baseline supplies register; this supplement supplies pitch-class
    preferences. A positive floor keeps the legacy candidate support. This is
    a demo heuristic (strength 0.75), not a tuned/evaluated quality improvement.
    Source sequences are counted once each, without overlapping-window inflation.
    """
    def __init__(self, baseline, compositions: list[dict], strength: float = .75, raga: str = "Mohanam"):
        self.baseline = baseline
        self.scale = SCALES[raga]
        self.strength = strength
        if not 0 <= strength <= 1:
            raise ValueError("strength must be between zero and one")
        self.prior = VariableOrderMarkov()
        sequences = [
            [self.scale.index(p) for p in passage["pitch_classes"]]
            for composition in compositions for passage in composition["passages"]
        ]
        self.prior.fit_sequences(sequences)

    def next_scores(self, context):
        scores = self.baseline.next_scores(context)
        # Do not join the pitch context across a rest/unknown event.
        tail = []
        for degree in reversed(context):
            if not is_note(degree):
                break
            tail.append(degree % len(self.scale))
        prior = self.prior.next_scores(list(reversed(tail)))
        total = sum(prior.values())
        if not total:
            return scores
        return {
            degree: score * (1 - self.strength + self.strength * len(self.scale)
                             * prior.get(degree % len(self.scale), 0) / total)
            if is_note(degree) else score
            for degree, score in scores.items()
        }
