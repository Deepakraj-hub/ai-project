"""Desktop notifications adapter placeholder."""

from __future__ import annotations

from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class NotificationsTool:
    name = "notifications"
    description = "Show desktop notifications for task progress and completion."
    permission_level = PermissionLevel.WRITE

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        return PermissionRequest(
            action="notifications.show",
            reason="Lily wants to notify the user.",
            risk_level=PermissionLevel.WRITE,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(True, "Notification recorded.", {"title": parameters.get("title"), "body": parameters.get("body")})
