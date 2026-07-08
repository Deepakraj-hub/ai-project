"""Background worker for Lily's autonomous agent with UI permission hooks."""

from __future__ import annotations

import os
import threading
from dataclasses import asdict
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from lily.brain.permissions import PermissionDecision, PermissionManager, PermissionRequest
from lily.brain.schema import AgentRunResult, TaskStatus
from lily.memory.memory import AgentMemory


class UiPermissionManager(PermissionManager):
    """Blocks tool execution until the desktop UI approves or denies."""

    def __init__(self, request_callback, memory: AgentMemory, trusted_mode: bool = True):
        super().__init__(auto_approve_read=True, trusted_mode=trusted_mode)
        self._request_callback = request_callback
        self._memory = memory

    def evaluate(self, request: PermissionRequest, approvals=None):
        approval_key = PermissionManager.approval_key(request)
        self._memory.record_event(
            None,
            "permission_request",
            {
                "approval_key": approval_key,
                "action": request.action,
                "tool_name": request.tool_name,
                "risk_level": request.risk_level.value,
                "affected_files": request.affected_files,
                "parameters": request.parameters,
            },
        )

        policy = self._memory.get_permission_policy(approval_key)
        if policy and policy.get("approved") and policy.get("always_allow"):
            decision = PermissionDecision(True, True, policy.get("reason", "Stored trusted policy."))
            self._record_decision(approval_key, request, decision)
            return decision

        decision = super().evaluate(request, approvals)
        if decision.approved:
            self._record_decision(approval_key, request, decision)
            return decision
        decision = self._request_callback(request)
        self._record_decision(approval_key, request, decision)
        if decision.approved and decision.always_allow:
            self._memory.save_permission_policy(
                approval_key,
                request.tool_name or "",
                request.risk_level.value,
                request.action,
                decision.approved,
                decision.always_allow,
                decision.reason,
            )
        return decision

    def _record_decision(self, approval_key: str, request: PermissionRequest, decision: PermissionDecision):
        self._memory.record_event(
            None,
            "permission_decision",
            {
                "approval_key": approval_key,
                "action": request.action,
                "tool_name": request.tool_name,
                "risk_level": request.risk_level.value,
                "approved": decision.approved,
                "always_allow": decision.always_allow,
                "reason": decision.reason,
            },
        )


class AgentSessionWorker(QThread):
    """Runs AutonomousAgent off the UI thread with permission prompts."""

    permission_required = Signal(dict)
    step_progress = Signal(str)
    finished_result = Signal(dict)
    error = Signal(str)

    def __init__(self, goal: str, parent=None):
        super().__init__(parent)
        self._goal = goal.strip()
        self._decision_event = threading.Event()
        self._pending_decision: PermissionDecision | None = None
        self._decision_lock = threading.Lock()

    def supply_permission(self, decision: PermissionDecision):
        with self._decision_lock:
            self._pending_decision = decision
        self._decision_event.set()

    def _request_permission(self, request: PermissionRequest) -> PermissionDecision:
        self._decision_event.clear()
        payload = asdict(request)
        payload["approval_key"] = PermissionManager.approval_key(request)
        self.permission_required.emit(payload)
        self._decision_event.wait()
        with self._decision_lock:
            decision = self._pending_decision or PermissionDecision(approved=False, reason="No decision supplied.")
            self._pending_decision = None
        return decision

    def run(self):
        try:
            from jarvis import SmartSearchEngine
            from lily.brain.agent import AutonomousAgent

            app_root = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            project_root = app_root / "projects"
            project_root.mkdir(parents=True, exist_ok=True)
            memory = AgentMemory(project_root / "lily_agent_memory.db")
            trusted_mode = os.getenv("LILY_TRUSTED_MODE", "1").strip().lower() not in {"0", "false", "no"}
            permission_manager = UiPermissionManager(self._request_permission, memory, trusted_mode=trusted_mode)
            agent = AutonomousAgent(
                project_root=project_root,
                memory=memory,
                search_engine=SmartSearchEngine(),
                permission_manager=permission_manager,
            )

            self.step_progress.emit("Planning task...")
            result: AgentRunResult = agent.run(goal=self._goal, max_steps=10)
            self.finished_result.emit(self._result_payload(result))
        except Exception as exc:
            self.error.emit(str(exc))

    @staticmethod
    def _result_payload(result: AgentRunResult) -> dict:
        artifacts = []
        preview_url = None
        for obs in result.observations:
            data = obs.data or {}
            path = data.get("path")
            if path and str(path).lower().endswith(".html"):
                artifacts.append(path)
                if not preview_url:
                    preview_url = Path(path).resolve().as_uri()
            url = data.get("url")
            if url:
                preview_url = url

        return {
            "task_id": result.task_id,
            "status": result.status.value,
            "goal": result.goal,
            "message": result.message,
            "preview_url": preview_url,
            "artifacts": artifacts,
            "requires_permission": result.requires_permission,
            "observations": [
                {
                    "step_id": obs.step_id,
                    "success": obs.success,
                    "summary": obs.summary,
                    "data": obs.data,
                    "error": obs.error,
                }
                for obs in result.observations
            ],
        }
