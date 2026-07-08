"""Skill memory and simple workflow promotion."""

from __future__ import annotations

from lily.memory.memory import AgentMemory


class SkillMemory:
    """Stores reusable workflows Lily can learn over time."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def maybe_promote_workflow(self, name: str, trigger: str, workflow: dict, repeated: bool = False) -> bool:
        if not repeated:
            return False
        self.memory.save_skill(name, trigger, workflow)
        return True
