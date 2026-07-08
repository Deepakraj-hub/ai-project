"""Screen vision tools for Lily."""

from __future__ import annotations

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class VisionTool:
    name = "vision"
    description = "Capture screenshots and analyze what is visible on the user's screen."
    permission_level = PermissionLevel.EXECUTE

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        operation = parameters.get("operation", "screenshot")
        return PermissionRequest(
            action=f"vision.{operation}",
            reason="Lily needs to capture the screen to understand the current desktop state.",
            risk_level=PermissionLevel.EXECUTE,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        operation = parameters.get("operation", "screenshot")
        if operation == "screenshot":
            return self._screenshot(context)
        if operation == "analyze_screen":
            shot = self._screenshot(context)
            if not shot.success:
                return shot
            analysis = self._analyze_image(shot.data["path"])
            data = dict(shot.data)
            data["analysis"] = analysis
            return ToolResult(True, "Captured and analyzed the current screen.", data)
        return ToolResult(False, f"Unsupported vision operation: {operation}", error="unsupported_operation")

    def _screenshot(self, context: ToolContext) -> ToolResult:
        results_dir = context.workspace_root / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        path = results_dir / f"screen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        ps_path = str(path).replace("'", "''")
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "Add-Type -AssemblyName System.Drawing; "
            "$bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds; "
            "$bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height; "
            "$graphics = [System.Drawing.Graphics]::FromImage($bmp); "
            "$graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size); "
            f"$bmp.Save('{ps_path}', [System.Drawing.Imaging.ImageFormat]::Png); "
            "$graphics.Dispose(); $bmp.Dispose();"
        )
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            capture_output=True,
            timeout=15,
        )
        if completed.returncode != 0 or not path.exists():
            return ToolResult(False, "Could not capture the screen.", error=completed.stderr)
        return ToolResult(True, f"Captured screen: {path}", {"path": str(path)})

    def _analyze_image(self, image_path: str) -> str:
        try:
            from jarvis import analyze_image

            return analyze_image(image_path)
        except Exception as exc:
            return f"Screen captured, but visual analysis was unavailable: {exc}"
