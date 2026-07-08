"""Git tool for safe repository inspection and common operations."""

from __future__ import annotations

import subprocess
from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class GitTool:
    name = "git"
    description = "Run git status, diff, log, and other approved repository commands."
    permission_level = PermissionLevel.READ

    READ_COMMANDS = {"status", "diff", "log", "show", "branch"}
    WRITE_COMMANDS = {"add", "commit", "pull", "push", "checkout", "switch", "merge", "rebase"}

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        operation = parameters.get("operation", "status")
        level = PermissionLevel.READ if operation in self.READ_COMMANDS else PermissionLevel.WRITE
        return PermissionRequest(
            action=f"git.{operation}",
            reason="Lily needs to inspect or update a git repository.",
            risk_level=level,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        operation = parameters.get("operation", "status")
        args = parameters.get("args", [])
        if isinstance(args, str):
            args = [args]
        command = ["git", operation, *args]
        try:
            completed = subprocess.run(
                command,
                cwd=str(context.workspace_root),
                text=True,
                capture_output=True,
                timeout=int(parameters.get("timeout", 60)),
            )
            data = {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}
            success = completed.returncode == 0
            return ToolResult(success, f"git {operation} completed." if success else f"git {operation} failed.", data)
        except Exception as exc:
            return ToolResult(False, f"Git operation failed: {exc}", error=str(exc))
