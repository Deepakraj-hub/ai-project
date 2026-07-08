"""Base classes for Lily tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from lily.brain.permissions import PermissionLevel, PermissionRequest


@dataclass(slots=True)
class ToolContext:
    """Context passed to every tool execution."""

    task_id: str
    workspace_root: Path
    allowed_roots: list[Path] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_path_allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        roots = [self.workspace_root, *self.allowed_roots]
        return any(str(resolved).lower().startswith(str(root.resolve()).lower()) for root in roots)


@dataclass(slots=True)
class ToolResult:
    """Normalized result returned by a tool."""

    success: bool
    summary: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class Tool(Protocol):
    """Protocol every Lily tool implements."""

    name: str
    description: str
    permission_level: PermissionLevel

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        """Return the approval request for this execution."""

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        """Run the tool and return a normalized observation."""
