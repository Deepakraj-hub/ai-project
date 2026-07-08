"""Structured file logger for agent events."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class JsonlLogger:
    """Append-only JSONL logger."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: str, payload: dict[str, Any]) -> None:
        record = {"timestamp": datetime.now().isoformat(), "event": event, **payload}
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")
