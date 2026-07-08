"""Post-task reflection for Lily."""

from __future__ import annotations

from lily.brain.schema import AgentObservation
from lily.memory.memory import AgentMemory


class ReflectionEngine:
    """Evaluates completed tasks and stores improvements."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def reflect(self, task_id: str, goal: str, observations: list[AgentObservation]) -> dict:
        success = bool(observations) and all(obs.success for obs in observations)
        failed = [obs for obs in observations if not obs.success]
        mistakes = [obs.summary for obs in failed]
        improvements = []
        if failed:
            improvements.append("Add more precise tool parameters before retrying failed steps.")
            improvements.append("Ask for permission earlier when a task requires writes or execution.")
        else:
            improvements.append("Reuse this plan shape for similar future tasks.")

        summary = (
            f"Task completed with {len(observations)} observations."
            if success
            else f"Task stopped with {len(failed)} failed observation(s)."
        )
        self.memory.save_reflection(task_id, success, summary, mistakes, improvements)
        return {
            "success": success,
            "summary": summary,
            "mistakes": mistakes,
            "improvements": improvements,
        }
