"""Web search tool backed by Lily's existing smart search engine."""

from __future__ import annotations

from typing import Any

from lily.brain.permissions import PermissionLevel, PermissionRequest
from lily.tools.base import ToolContext, ToolResult


class SearchTool:
    name = "search"
    description = "Search the web and summarize live results for current information."
    permission_level = PermissionLevel.NETWORK

    def __init__(self, search_engine=None):
        self.search_engine = search_engine

    def permission_request(self, parameters: dict[str, Any], context: ToolContext) -> PermissionRequest:
        return PermissionRequest(
            action=f"search.web: {parameters.get('query', '')}",
            reason="Lily needs live information from the web.",
            risk_level=PermissionLevel.NETWORK,
            tool_name=self.name,
            parameters=parameters,
        )

    def execute(self, parameters: dict[str, Any], context: ToolContext) -> ToolResult:
        query = parameters["query"]
        if not self.search_engine:
            return ToolResult(False, "No search engine is configured.", error="search_engine_missing")
        payload = self.search_engine.search(query, force=bool(parameters.get("force", True)))
        return ToolResult(
            success=bool(payload.get("used") or payload.get("results")),
            summary=f"Search completed for: {query}",
            data=payload,
        )
