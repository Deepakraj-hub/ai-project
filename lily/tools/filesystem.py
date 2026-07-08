"""Filesystem tool with workspace-aware safety checks."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class FilesystemTool:
    name = "filesystem"
    description = "Read, write, list, copy, move, rename, delete, and search files inside allowed workspaces."
    permission_level = PermissionLevel.WRITE

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        operation = parameters.get("operation", "read")
        level = PermissionLevel.READ
        if operation in {"write", "copy", "move", "rename"}:
            level = PermissionLevel.WRITE
        if operation == "delete":
            level = PermissionLevel.DESTRUCTIVE
        path = str(parameters.get("path", ""))
        return PermissionRequest(
            action=f"filesystem.{operation}",
            reason=f"Lily needs to {operation} a file or folder.",
            risk_level=level,
            affected_files=[path] if path else [],
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        operation = parameters.get("operation", "read")
        try:
            if operation == "read":
                return self._read(parameters, context)
            if operation == "list":
                return self._list(parameters, context)
            if operation == "search":
                return self._search(parameters, context)
            if operation == "write":
                return self._write(parameters, context)
            if operation == "copy":
                return self._copy(parameters, context)
            if operation in {"move", "rename"}:
                return self._move(parameters, context)
            if operation == "delete":
                return self._delete(parameters, context)
            return ToolResult(False, f"Unknown filesystem operation: {operation}", error="unknown_operation")
        except Exception as exc:
            return ToolResult(False, f"Filesystem operation failed: {exc}", error=str(exc))

    def _path(self, raw_path: str, context: ToolContext) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = context.workspace_root / path
        path = path.resolve()
        if not context.is_path_allowed(path):
            raise PermissionError(f"Path is outside allowed roots: {path}")
        return path

    def _read(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        path = self._path(parameters["path"], context)
        text = path.read_text(encoding=parameters.get("encoding", "utf-8"), errors="replace")
        return ToolResult(True, f"Read {path}", {"path": str(path), "content": text})

    def _list(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        path = self._path(parameters.get("path", "."), context)
        entries = []
        for child in path.iterdir():
            entries.append({"name": child.name, "path": str(child), "type": "dir" if child.is_dir() else "file"})
        return ToolResult(True, f"Listed {path}", {"path": str(path), "entries": entries})

    def _search(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        path = self._path(parameters.get("path", "."), context)
        pattern = parameters.get("pattern", "*")
        matches = [str(p) for p in path.rglob(pattern)]
        return ToolResult(True, f"Found {len(matches)} matches", {"matches": matches[:500], "total": len(matches)})

    def _write(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        path = self._path(parameters["path"], context)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = parameters.get("content", "")
        path.write_text(content, encoding=parameters.get("encoding", "utf-8"))
        return ToolResult(True, f"Wrote {path}", {"path": str(path), "bytes": len(content.encode("utf-8"))})

    def _copy(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        src = self._path(parameters["path"], context)
        dst = self._path(parameters["target"], context)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)
        return ToolResult(True, f"Copied {src} to {dst}", {"source": str(src), "target": str(dst)})

    def _move(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        src = self._path(parameters["path"], context)
        dst = self._path(parameters["target"], context)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return ToolResult(True, f"Moved {src} to {dst}", {"source": str(src), "target": str(dst)})

    def _delete(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        path = self._path(parameters["path"], context)
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        return ToolResult(True, f"Deleted {path}", {"path": str(path)})
