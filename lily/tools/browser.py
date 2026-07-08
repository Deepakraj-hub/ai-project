"""Browser automation for opening local previews and URLs."""

from __future__ import annotations

import webbrowser
from pathlib import Path
from typing import Any
from urllib.parse import quote

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class BrowserTool:
    name = "browser"
    description = "Open local HTML previews or URLs in the default browser."
    permission_level = PermissionLevel.NETWORK

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        operation = parameters.get("operation", "open")
        target = parameters.get("path") or parameters.get("url") or "unknown"
        return PermissionRequest(
            action=f"browser.{operation}: {target}",
            reason="Lily wants to open a browser page or finished preview.",
            risk_level=PermissionLevel.NETWORK,
            affected_files=[str(target)] if parameters.get("path") else [],
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        operation = parameters.get("operation", "open")
        if operation != "open":
            return ToolResult(False, f"Unsupported browser operation: {operation}", error="unsupported_operation")

        url = parameters.get("url")
        if not url and parameters.get("path"):
            path = Path(parameters["path"])
            if not path.is_absolute():
                path = (context.workspace_root / path).resolve()
            if not path.exists():
                return ToolResult(False, f"File not found: {path}", error="not_found")
            url = path.as_uri()

        if not url:
            return ToolResult(False, "No URL or path provided.", error="missing_target")

        opened = webbrowser.open(url, new=2)
        if not opened:
            return ToolResult(False, f"Could not open browser for {url}", error="open_failed")
        return ToolResult(True, f"Opened browser page: {url}", {"url": url, "path": parameters.get("path")})
