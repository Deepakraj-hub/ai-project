"""Fact memory facade over Lily's existing SQLite database."""

from __future__ import annotations

from lily.memory.memory import AgentMemory


class FactMemory:
    """Stores durable project and user facts."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def remember(self, project_path: str, key: str, value: str) -> None:
        self.memory.remember_project(project_path, key, value)
