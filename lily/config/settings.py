"""Runtime settings for Lily's autonomous agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    workspace_root: Path
    database_path: Path
    model_provider: str = "ollama"
    model_name: str = "gemma4:cloud"


def load_settings(project_root: str | Path | None = None) -> Settings:
    root = Path(project_root or os.getcwd()).resolve()
    return Settings(
        project_root=root,
        workspace_root=root / "workspace",
        database_path=root / "jarvis_memory.db",
        model_provider=os.getenv("LILY_MODEL_PROVIDER", "ollama"),
        model_name=os.getenv("LILY_MODEL_NAME", "gemma4:cloud"),
    )
