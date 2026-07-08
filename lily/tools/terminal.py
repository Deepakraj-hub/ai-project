"""Terminal execution tool with conservative dangerous-command detection."""

from __future__ import annotations

import re
import subprocess
from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class TerminalTool:
    name = "terminal"
    description = "Execute shell commands in the task workspace and capture stdout/stderr."
    permission_level = PermissionLevel.EXECUTE

    DANGEROUS_PATTERNS = [
        r"\brm\b",
        r"\bdel\b",
        r"\brmdir\b",
        r"\bformat\b",
        r"\bshutdown\b",
        r"\brestart-computer\b",
        r"\breg\s+delete\b",
        r"\bpip\s+install\b",
        r"\bnpm\s+install\b",
        r"\buv\s+pip\s+install\b",
    ]

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        command = parameters.get("command", "")
        level = PermissionLevel.DESTRUCTIVE if self._is_dangerous(command) else PermissionLevel.EXECUTE
        return PermissionRequest(
            action=f"terminal.run: {command}",
            reason="Lily needs to execute a terminal command for the task.",
            risk_level=level,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        command = parameters["command"]
        timeout = int(parameters.get("timeout", 60))
        cwd = parameters.get("cwd")
        run_cwd = context.workspace_root if not cwd else context.workspace_root / cwd
        if not context.is_path_allowed(run_cwd):
            return ToolResult(False, "Command working directory is outside allowed roots.", error="cwd_not_allowed")
        try:
            completed = subprocess.run(
                command,
                cwd=str(run_cwd),
                shell=True,
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            output = {
                "returncode": completed.returncode,
                "stdout": completed.stdout[-12000:],
                "stderr": completed.stderr[-12000:],
            }
            success = completed.returncode == 0
            summary = "Command completed." if success else f"Command failed with exit code {completed.returncode}."
            return ToolResult(success, summary, output, None if success else completed.stderr[-2000:])
        except subprocess.TimeoutExpired as exc:
            return ToolResult(False, f"Command timed out after {timeout}s.", error=str(exc))

    def _is_dangerous(self, command: str) -> bool:
        lower = command.lower()
        return any(re.search(pattern, lower) for pattern in self.DANGEROUS_PATTERNS)
