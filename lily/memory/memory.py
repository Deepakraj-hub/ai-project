"""SQLite-backed long-term memory for Lily's autonomous agent."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


class AgentMemory:
    """Stores tasks, steps, project memory, learned skills, and reflections."""

    def __init__(self, db_path: str | Path = "jarvis_memory.db"):
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_tables()

    def _init_tables(self) -> None:
        with self.lock:
            cursor = self.conn.cursor()
            cursor.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_tasks (
                    task_id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    workspace_path TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS agent_steps (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    step_id TEXT,
                    title TEXT,
                    status TEXT,
                    reasoning_json TEXT,
                    observation_json TEXT,
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS project_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_path TEXT,
                    key TEXT,
                    value TEXT,
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS skill_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    trigger TEXT,
                    workflow_json TEXT,
                    success_count INTEGER DEFAULT 0,
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS agent_reflections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    success INTEGER,
                    summary TEXT,
                    mistakes TEXT,
                    improvements TEXT,
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS agent_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    event_type TEXT,
                    payload_json TEXT,
                    timestamp TEXT
                );

                CREATE TABLE IF NOT EXISTS permission_policies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    policy_key TEXT UNIQUE,
                    tool_name TEXT,
                    risk_level TEXT,
                    action TEXT,
                    approved INTEGER,
                    always_allow INTEGER,
                    reason TEXT,
                    timestamp TEXT
                );
                """
            )
            self.conn.commit()

    def start_task(self, task_id: str, goal: str, workspace_path: str) -> None:
        now = datetime.now().isoformat()
        with self.lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO agent_tasks
                (task_id, goal, status, workspace_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, COALESCE((SELECT created_at FROM agent_tasks WHERE task_id = ?), ?), ?)
                """,
                (task_id, goal, "running", workspace_path, task_id, now, now),
            )
            self.conn.commit()

    def record_event(self, task_id: str | None, event_type: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO agent_events (task_id, event_type, payload_json, timestamp)
                VALUES (?, ?, ?, ?)
                """,
                (task_id, event_type, json.dumps(payload, default=str), datetime.now().isoformat()),
            )
            self.conn.commit()

    def save_permission_policy(
        self,
        policy_key: str,
        tool_name: str,
        risk_level: str,
        action: str,
        approved: bool,
        always_allow: bool,
        reason: str,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO permission_policies
                (policy_key, tool_name, risk_level, action, approved, always_allow, reason, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    policy_key,
                    tool_name,
                    risk_level,
                    action,
                    1 if approved else 0,
                    1 if always_allow else 0,
                    reason,
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()

    def get_permission_policy(self, policy_key: str) -> dict[str, Any] | None:
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT policy_key, tool_name, risk_level, action, approved, always_allow, reason
            FROM permission_policies WHERE policy_key = ?
            """,
            (policy_key,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        key, tool_name, risk_level, action, approved, always_allow, reason = row
        return {
            "policy_key": key,
            "tool_name": tool_name,
            "risk_level": risk_level,
            "action": action,
            "approved": bool(approved),
            "always_allow": bool(always_allow),
            "reason": reason,
        }

    def update_task_status(self, task_id: str, status: str) -> None:
        with self.lock:
            self.conn.execute(
                "UPDATE agent_tasks SET status = ?, updated_at = ? WHERE task_id = ?",
                (status, datetime.now().isoformat(), task_id),
            )
            self.conn.commit()

    def record_step(
        self,
        task_id: str,
        step_id: str,
        title: str,
        status: str,
        reasoning: dict[str, Any] | None = None,
        observation: dict[str, Any] | None = None,
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO agent_steps
                (task_id, step_id, title, status, reasoning_json, observation_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    step_id,
                    title,
                    status,
                    json.dumps(reasoning or {}),
                    json.dumps(observation or {}),
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()

    def remember_project(self, project_path: str, key: str, value: str) -> None:
        with self.lock:
            self.conn.execute(
                "INSERT INTO project_memory (project_path, key, value, timestamp) VALUES (?, ?, ?, ?)",
                (project_path, key, value, datetime.now().isoformat()),
            )
            self.conn.commit()

    def save_skill(self, name: str, trigger: str, workflow: dict[str, Any]) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO skill_memory (name, trigger, workflow_json, success_count, timestamp)
                VALUES (?, ?, ?, 1, ?)
                """,
                (name, trigger, json.dumps(workflow), datetime.now().isoformat()),
            )
            self.conn.commit()

    def get_skills(self, limit: int = 20) -> list[dict[str, Any]]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name, trigger, workflow_json, success_count FROM skill_memory ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
        return [
            {
                "name": name,
                "trigger": trigger,
                "workflow": json.loads(workflow_json or "{}"),
                "success_count": success_count,
            }
            for name, trigger, workflow_json, success_count in rows
        ]

    def save_reflection(
        self,
        task_id: str,
        success: bool,
        summary: str,
        mistakes: list[str],
        improvements: list[str],
    ) -> None:
        with self.lock:
            self.conn.execute(
                """
                INSERT INTO agent_reflections
                (task_id, success, summary, mistakes, improvements, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    task_id,
                    1 if success else 0,
                    summary,
                    json.dumps(mistakes),
                    json.dumps(improvements),
                    datetime.now().isoformat(),
                ),
            )
            self.conn.commit()
