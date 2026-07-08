"""Windows desktop automation tool for simple app launch and text entry."""

from __future__ import annotations

import platform
import re
import subprocess
import time
from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class DesktopTool:
    name = "desktop"
    description = "Open desktop apps such as Notepad and type text into the active window."
    permission_level = PermissionLevel.EXECUTE

    SAFE_APPS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
    }

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        operation = parameters.get("operation", "open_app")
        app = parameters.get("app", "desktop")
        text = parameters.get("text", "")
        reason = f"Lily wants to control the desktop: {operation} {app}."
        if text:
            reason += f" Text to type: {text!r}"
        return PermissionRequest(
            action=f"desktop.{operation}: {app}",
            reason=reason,
            risk_level=PermissionLevel.EXECUTE,
            tool_name=self.name,
            parameters={k: v for k, v in parameters.items() if k != "text" or len(str(v)) <= 500},
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        if platform.system().lower() != "windows":
            return ToolResult(False, "Desktop automation is currently implemented for Windows only.", error="unsupported_os")

        operation = parameters.get("operation", "open_app")
        if operation == "open_app":
            return self._open_app(parameters)
        if operation == "open_and_type":
            return self._open_and_type(parameters)
        if operation == "type_text":
            return self._type_text(parameters.get("text", ""))
        return ToolResult(False, f"Unsupported desktop operation: {operation}", error="unsupported_operation")

    def _open_app(self, parameters: dict[str, Any]) -> ToolResult:
        app_name = str(parameters.get("app", "")).lower().strip()
        app = self.SAFE_APPS.get(app_name)
        if not app:
            return ToolResult(False, f"Desktop app is not allowlisted yet: {app_name}", error="app_not_allowlisted")
        subprocess.Popen([app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ToolResult(True, f"Opened {app_name}.", {"app": app_name})

    def _open_and_type(self, parameters: dict[str, Any]) -> ToolResult:
        app_result = self._open_app(parameters)
        if not app_result.success:
            return app_result
        delay = float(parameters.get("delay_seconds", 0.8))
        time.sleep(max(0.1, delay))
        text_result = self._type_text(parameters.get("text", ""))
        if not text_result.success:
            return text_result
        return ToolResult(
            True,
            f"Opened {parameters.get('app')} and typed text.",
            {"app": parameters.get("app"), "text": parameters.get("text", "")},
        )

    def _type_text(self, text: str) -> ToolResult:
        if not text:
            return ToolResult(False, "No text provided to type.", error="missing_text")
        escaped = self._sendkeys_escape(text)
        ps_script = (
            "$ws = New-Object -ComObject WScript.Shell; "
            "Start-Sleep -Milliseconds 250; "
            "$ws.SendKeys('" + escaped + "');"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            text=True,
            capture_output=True,
            timeout=10,
        )
        if completed.returncode != 0:
            return ToolResult(False, "Could not type into the active desktop window.", error=completed.stderr)
        return ToolResult(True, "Typed text into the active window.", {"text": text})

    def _sendkeys_escape(self, text: str) -> str:
        escaped = text.replace("'", "''")
        escaped = re.sub(r"([+^%~(){}\[\]])", r"{\1}", escaped)
        escaped = escaped.replace("\n", "{ENTER}")
        return escaped
