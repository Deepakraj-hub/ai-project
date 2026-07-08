"""Conversation and task history adapters."""

from __future__ import annotations

from lily.memory.memory import AgentMemory


class HistoryMemory:
    """Small facade for task history queries."""

    def __init__(self, memory: AgentMemory):
        self.memory = memory

    def recent_tasks(self, limit: int = 10) -> list[dict[str, str]]:
        cursor = self.memory.conn.cursor()
        cursor.execute(
            "SELECT task_id, goal, status, updated_at FROM agent_tasks ORDER BY updated_at DESC LIMIT ?",
            (limit,),
        )
        return [
            {"task_id": task_id, "goal": goal, "status": status, "updated_at": updated_at}
            for task_id, goal, status, updated_at in cursor.fetchall()
        ]
