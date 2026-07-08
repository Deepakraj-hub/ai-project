"""Clipboard adapter placeholder.

The desktop UI can later inject a native clipboard backend. Keeping this tool
in the registry now lets the agent core stay unchanged when that happens.
"""

from __future__ import annotations

from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class ClipboardTool:
    name = "clipboard"
    description = "Copy text to clipboard, paste text, and inspect clipboard history when a desktop backend is available."
    permission_level = PermissionLevel.WRITE

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        return PermissionRequest(
            action=f"clipboard.{parameters.get('operation', 'copy')}",
            reason="Lily needs clipboard access.",
            risk_level=PermissionLevel.WRITE,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(False, "Clipboard backend is not connected yet.", error="not_implemented")
