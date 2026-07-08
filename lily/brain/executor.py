"""Tool execution pipeline for Lily."""

from __future__ import annotations

from dataclasses import asdict

from lily.brain.permissions import PermissionDecision, PermissionManager
from lily.brain.schema import AgentObservation, ReasoningTrace
from lily.tools.base import ToolContext
from lily.tools.registry import ToolRegistry


class ExecutionBlocked(Exception):
    """Raised when a tool needs permission that has not been granted."""

    def __init__(self, request_payload: dict):
        super().__init__("Permission required")
        self.request_payload = request_payload


class Executor:
    """Runs selected tools only after permission checks pass."""

    def __init__(self, tool_registry: ToolRegistry, permission_manager: PermissionManager | None = None):
        self.tool_registry = tool_registry
        self.permission_manager = permission_manager or PermissionManager()

    def execute(
        self,
        step_id: str,
        trace: ReasoningTrace,
        context: ToolContext,
        approvals: dict[str, PermissionDecision] | None = None,
    ) -> AgentObservation:
        if not trace.tool_name:
            return AgentObservation(step_id, True, "No external tool required.", {"reasoning": asdict(trace)})

        tool = self.tool_registry.get(trace.tool_name)
        request = tool.permission_request(trace.parameters, context)
        decision = self.permission_manager.evaluate(request, approvals)
        if not decision.approved:
            payload = asdict(request)
            payload["approval_key"] = PermissionManager.approval_key(request)
            payload["decision_reason"] = decision.reason
            raise ExecutionBlocked(payload)

        result = tool.execute(trace.parameters, context)
        return AgentObservation(
            step_id=step_id,
            success=result.success,
            summary=result.summary,
            data=result.data,
            error=result.error,
        )
