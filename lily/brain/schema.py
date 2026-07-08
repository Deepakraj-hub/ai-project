"""Shared data structures for Lily's autonomous agent loop."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class TaskStatus(str, Enum):
    """Lifecycle state for an autonomous task."""

    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(str, Enum):
    """Lifecycle state for one plan step."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class PlanStep:
    """One concrete step in an agent plan."""

    id: str
    title: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    depends_on: list[str] = field(default_factory=list)
    tool_hint: str | None = None

    @classmethod
    def create(cls, title: str, description: str = "", tool_hint: str | None = None) -> "PlanStep":
        return cls(id=str(uuid4()), title=title.strip(), description=description.strip(), tool_hint=tool_hint)


@dataclass(slots=True)
class TaskPlan:
    """A decomposed plan for a user goal."""

    task_id: str
    goal: str
    steps: list[PlanStep]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(slots=True)
class ReasoningTrace:
    """Structured reasoning record before Lily acts."""

    goal: str
    current_state: str
    possible_actions: list[str]
    best_action: str
    confidence: float
    expected_result: str
    tool_name: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentObservation:
    """Result observed after a tool or internal action runs."""

    step_id: str
    success: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass(slots=True)
class AgentRunResult:
    """Final report for an autonomous task run."""

    task_id: str
    status: TaskStatus
    goal: str
    observations: list[AgentObservation]
    message: str
    requires_permission: dict[str, Any] | None = None
