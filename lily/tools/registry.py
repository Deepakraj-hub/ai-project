"""Tool registry and discovery."""

from __future__ import annotations

from lily.tools.base import Tool


class ToolRegistry:
    """Runtime registry for discoverable tools."""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def discover(self) -> list[dict[str, str]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "permission_level": tool.permission_level.value,
            }
            for tool in self._tools.values()
        ]

    def names(self) -> list[str]:
        return sorted(self._tools)


def build_default_registry(search_engine=None) -> ToolRegistry:
    """Build Lily's default tool registry."""

    from lily.tools.browser import BrowserTool
    from lily.tools.clipboard import ClipboardTool
    from lily.tools.desktop import DesktopTool
    from lily.tools.email import EmailTool
    from lily.tools.filesystem import FilesystemTool
    from lily.tools.git import GitTool
    from lily.tools.notifications import NotificationsTool
    from lily.tools.python_executor import PythonExecutorTool
    from lily.tools.search import SearchTool
    from lily.tools.terminal import TerminalTool
    from lily.tools.vision import VisionTool

    registry = ToolRegistry()
    registry.register(FilesystemTool())
    registry.register(TerminalTool())
    registry.register(SearchTool(search_engine=search_engine))
    registry.register(PythonExecutorTool())
    registry.register(GitTool())
    registry.register(ClipboardTool())
    registry.register(DesktopTool())
    registry.register(BrowserTool())
    registry.register(VisionTool())
    registry.register(EmailTool())
    registry.register(NotificationsTool())
    return registry
