"""Sandbox-lite Python execution tool."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class PythonExecutorTool:
    name = "python_executor"
    description = "Run short Python snippets in the task workspace and capture output."
    permission_level = PermissionLevel.EXECUTE

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        return PermissionRequest(
            action="python.execute",
            reason="Lily needs to run Python code to compute or verify something.",
            risk_level=PermissionLevel.EXECUTE,
            tool_name=self.name,
            parameters={"code_preview": parameters.get("code", "")[:500]},
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        code = parameters["code"]
        timeout = int(parameters.get("timeout", 30))
        try:
            completed = subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(context.workspace_root),
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            data = {
                "returncode": completed.returncode,
                "stdout": completed.stdout[-12000:],
                "stderr": completed.stderr[-12000:],
            }
            success = completed.returncode == 0
            return ToolResult(success, "Python snippet completed." if success else "Python snippet failed.", data)
        except subprocess.TimeoutExpired as exc:
            return ToolResult(False, f"Python snippet timed out after {timeout}s.", error=str(exc))
