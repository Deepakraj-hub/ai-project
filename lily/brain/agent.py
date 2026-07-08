"""Autonomous Lily agent loop."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from lily.brain.executor import ExecutionBlocked, Executor
from lily.brain.permissions import PermissionDecision, PermissionManager
from lily.brain.planner import Planner
from lily.brain.reasoner import Reasoner
from lily.brain.reflection import ReflectionEngine
from lily.brain.schema import AgentObservation, AgentRunResult, StepStatus, TaskStatus
from lily.memory.memory import AgentMemory
from lily.tools.base import ToolContext
from lily.tools.registry import ToolRegistry, build_default_registry
from lily.workspace.manager import WorkspaceManager


class AutonomousAgent:
    """Hermes-inspired autonomous engine that gives Lily controlled hands."""

    def __init__(
        self,
        project_root: str | Path,
        memory: AgentMemory | None = None,
        workspace_manager: WorkspaceManager | None = None,
        tool_registry: ToolRegistry | None = None,
        planner: Planner | None = None,
        permission_manager: PermissionManager | None = None,
        search_engine=None,
    ):
        self.project_root = Path(project_root).resolve()
        self.workspace_manager = workspace_manager or WorkspaceManager(self.project_root / "workspace")
        self.memory = memory or AgentMemory(self.project_root / "jarvis_memory.db")
        self.tool_registry = tool_registry or build_default_registry(search_engine=search_engine)
        self.permission_manager = permission_manager or PermissionManager()
        self.planner = planner or Planner()
        self.reasoner = Reasoner(self.tool_registry, self.project_root)
        self.executor = Executor(self.tool_registry, self.permission_manager)
        self.reflection = ReflectionEngine(self.memory)

    def run(
        self,
        goal: str,
        task_id: str | None = None,
        max_steps: int = 8,
        approvals: dict[str, dict[str, Any]] | None = None,
    ) -> AgentRunResult:
        task_id = task_id or self.workspace_manager.create_task_id()
        task_workspace = self.workspace_manager.ensure_task_workspace(task_id)
        plan = self.planner.create_plan(task_id, goal)
        plan.steps = plan.steps[:max_steps]
        self.workspace_manager.save_plan(plan)
        self.memory.start_task(task_id, goal, str(task_workspace))
        self.memory.record_event(task_id, "task_started", {"goal": goal, "workspace": str(task_workspace)})

        approval_decisions = self._parse_approvals(approvals)
        observations: list[AgentObservation] = []
        context = ToolContext(
            task_id=task_id,
            workspace_root=task_workspace,
            allowed_roots=[self.project_root],
            metadata={"goal": goal},
        )

        try:
            for step in plan.steps:
                step.status = StepStatus.RUNNING
                trace = self.reasoner.reason(plan, step, task_workspace)
                self.memory.record_step(task_id, step.id, step.title, step.status.value, asdict(trace), None)
                self.memory.record_event(
                    task_id,
                    "reasoning",
                    {"step_id": step.id, "title": step.title, "trace": asdict(trace)},
                )
                try:
                    observation = self.executor.execute(step.id, trace, context, approval_decisions)
                except ExecutionBlocked as blocked:
                    self.memory.update_task_status(task_id, TaskStatus.WAITING_FOR_PERMISSION.value)
                    self.memory.record_event(task_id, "permission_required", blocked.request_payload)
                    return AgentRunResult(
                        task_id=task_id,
                        status=TaskStatus.WAITING_FOR_PERMISSION,
                        goal=goal,
                        observations=observations,
                        message="Lily needs approval before continuing.",
                        requires_permission=blocked.request_payload,
                    )

                observations.append(observation)
                self.workspace_manager.append_observation(task_id, observation)
                self.memory.record_event(task_id, "observation", asdict(observation))
                step.status = StepStatus.COMPLETED if observation.success else StepStatus.FAILED
                self.memory.record_step(
                    task_id,
                    step.id,
                    step.title,
                    step.status.value,
                    asdict(trace),
                    asdict(observation),
                )
                if not observation.success:
                    break

            reflection = self.reflection.reflect(task_id, goal, observations)
            status = TaskStatus.COMPLETED if reflection["success"] else TaskStatus.FAILED
            self.memory.update_task_status(task_id, status.value)
            self.memory.record_event(task_id, "task_finished", {"status": status.value, "reflection": reflection})
            message = self._final_message(goal, observations, reflection)
            return AgentRunResult(task_id, status, goal, observations, message)
        except Exception as exc:
            observation = AgentObservation("agent", False, "Agent loop crashed.", error=str(exc))
            observations.append(observation)
            self.memory.update_task_status(task_id, TaskStatus.FAILED.value)
            self.memory.record_event(task_id, "task_error", {"error": str(exc)})
            return AgentRunResult(task_id, TaskStatus.FAILED, goal, observations, f"Lily agent failed: {exc}")

    def discover_tools(self) -> list[dict[str, str]]:
        return self.tool_registry.discover()

    def _parse_approvals(self, approvals: dict[str, dict[str, Any]] | None) -> dict[str, PermissionDecision]:
        parsed: dict[str, PermissionDecision] = {}
        for key, value in (approvals or {}).items():
            parsed[key] = PermissionDecision(
                approved=bool(value.get("approved")),
                always_allow=bool(value.get("always_allow", False)),
                reason=str(value.get("reason", "")),
            )
        return parsed

    def _final_message(self, goal: str, observations: list[AgentObservation], reflection: dict) -> str:
        lines = [f"Goal: {goal}", reflection["summary"]]
        for obs in observations[-5:]:
            state = "OK" if obs.success else "FAILED"
            lines.append(f"{state}: {obs.summary}")
            if obs.data.get("analysis"):
                lines.append("Screen analysis: " + str(obs.data["analysis"])[:1200])
        if reflection.get("improvements"):
            lines.append("Next improvement: " + reflection["improvements"][0])
        return "\n".join(lines)
