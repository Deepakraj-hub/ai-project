"""Email tool placeholder with strict permission requirements."""

from __future__ import annotations

from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class EmailTool:
    name = "email"
    description = "Draft and send email through a configured provider."
    permission_level = PermissionLevel.EXTERNAL_SEND

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        return PermissionRequest(
            action="email.send",
            reason="Lily needs approval before sending an email.",
            risk_level=PermissionLevel.EXTERNAL_SEND,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        return ToolResult(False, "Email provider is not configured yet.", error="not_implemented")
