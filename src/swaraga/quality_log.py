"""Structured data-quality log (PRD section 10 deliverable).

Every repair, flag and drop the pipeline performs is recorded here with the
record id it applies to, then written out as both JSONL (machine-readable) and
Markdown (human-readable).
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

SEVERITIES = ("info", "warning", "error")


@dataclass
class QualityEvent:
    """One thing the pipeline noticed or changed."""

    stage: str                      # clean / normalize / validate / split
    record_id: Optional[str]        # composition id, or None for dataset-level events
    code: str                       # stable machine-readable code
    severity: str                   # info / warning / error
    message: str
    field_name: Optional[str] = None
    before: Optional[Any] = None
    after: Optional[Any] = None
    details: Dict[str, Any] = field(default_factory=dict)


class QualityLog:
    """Collects :class:`QualityEvent` records and renders the reports."""

    def __init__(self) -> None:
        self.events: List[QualityEvent] = []
        self.started_at = datetime.now(timezone.utc)

    # -- recording ----------------------------------------------------------

    def add(
        self,
        stage: str,
        code: str,
        message: str,
        *,
        record_id: Optional[str] = None,
        severity: str = "info",
        field_name: Optional[str] = None,
        before: Optional[Any] = None,
        after: Optional[Any] = None,
        **details: Any,
    ) -> None:
        if severity not in SEVERITIES:
            raise ValueError(f"unknown severity {severity!r}")
        self.events.append(
            QualityEvent(
                stage=stage,
                record_id=record_id,
                code=code,
                severity=severity,
                message=message,
                field_name=field_name,
                before=before,
                after=after,
                details=details,
            )
        )

    def info(self, stage: str, code: str, message: str, **kwargs: Any) -> None:
        self.add(stage, code, message, severity="info", **kwargs)

    def warning(self, stage: str, code: str, message: str, **kwargs: Any) -> None:
        self.add(stage, code, message, severity="warning", **kwargs)

    def error(self, stage: str, code: str, message: str, **kwargs: Any) -> None:
        self.add(stage, code, message, severity="error", **kwargs)

    # -- summaries ----------------------------------------------------------

    def counts_by_code(self) -> Dict[str, int]:
        return dict(Counter(event.code for event in self.events))

    def counts_by_severity(self) -> Dict[str, int]:
        counts = Counter(event.severity for event in self.events)
        return {severity: counts.get(severity, 0) for severity in SEVERITIES}

    def affected_records(self) -> int:
        return len({event.record_id for event in self.events if event.record_id})

    # -- output -------------------------------------------------------------

    def write_jsonl(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            for event in self.events:
                handle.write(json.dumps(asdict(event), ensure_ascii=False) + "\n")

    def write_markdown(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        by_code: Dict[str, List[QualityEvent]] = defaultdict(list)
        for event in self.events:
            by_code[event.code].append(event)

        severity_counts = self.counts_by_severity()
        lines: List[str] = [
            "# Data-quality log",
            "",
            f"Generated: {self.started_at.isoformat(timespec='seconds')}",
            "",
            f"- Total events: **{len(self.events)}**",
            f"- Errors: **{severity_counts['error']}** | "
            f"Warnings: **{severity_counts['warning']}** | "
            f"Info: **{severity_counts['info']}**",
            f"- Records touched by at least one event: **{self.affected_records()}**",
            "",
            "## Events by code",
            "",
            "| Code | Severity | Count | Stage |",
            "| --- | --- | ---: | --- |",
        ]

        # Most severe first, then most frequent first.
        ordered = sorted(
            by_code.items(),
            key=lambda item: (-SEVERITIES.index(_worst(item[1])), -len(item[1])),
        )
        for code, events in ordered:
            stages = sorted({event.stage for event in events})
            lines.append(
                f"| `{code}` | {_worst(events)} | {len(events)} | {', '.join(stages)} |"
            )

        lines += ["", "## Detail", ""]
        for code, events in ordered:
            lines.append(f"### `{code}` ({len(events)})")
            lines.append("")
            for event in events:
                target = f"`{event.record_id}`" if event.record_id else "_dataset_"
                detail = f"{target} - {event.message}"
                if event.field_name:
                    detail += f" (field: `{event.field_name}`)"
                lines.append(f"- {detail}")
            lines.append("")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _worst(events: List[QualityEvent]) -> str:
    """Highest severity present in ``events``."""
    return max((event.severity for event in events), key=SEVERITIES.index)
