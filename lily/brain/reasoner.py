"""Reasoning and tool-selection for Lily."""

from __future__ import annotations

from pathlib import Path

from lily.brain.schema import PlanStep, ReasoningTrace, TaskPlan
from lily.tools.registry import ToolRegistry
from lily.tools.website_builder import build_interactive_website_html, website_output_path


class Reasoner:
    """Chooses the next concrete action for a plan step."""

    def __init__(self, tool_registry: ToolRegistry, project_root: Path | None = None):
        self.tool_registry = tool_registry
        self.project_root = project_root

    def reason(self, plan: TaskPlan, step: PlanStep, workspace_root: Path) -> ReasoningTrace:
        tool_name = self._select_tool(step)
        parameters = self._build_parameters(plan.goal, step, tool_name, workspace_root)
        possible_actions = [
            f"Use {name}" for name in self.tool_registry.names()
        ] + ["Ask user for clarification", "Mark step complete if no tool is required"]
        return ReasoningTrace(
            goal=plan.goal,
            current_state=f"Executing step: {step.title}",
            possible_actions=possible_actions,
            best_action=f"Use {tool_name}" if tool_name else "Internal verification/reporting",
            confidence=0.62 if tool_name else 0.7,
            expected_result=f"Progress on: {step.title}",
            tool_name=tool_name,
            parameters=parameters,
        )

    def _select_tool(self, step: PlanStep) -> str | None:
        if step.tool_hint in self.tool_registry.names():
            return step.tool_hint
        text = f"{step.title} {step.description}".lower()
        if "understand the goal" in text:
            return None
        if self._mentions_live_search(text):
            return "search"
        if any(word in text for word in ["git", "diff", "commit", "status"]):
            return "git"
        if any(word in text for word in ["run", "test", "compile", "server", "command", "verify"]):
            return "terminal"
        if any(word in text for word in ["python", "calculate", "parse"]):
            return "python_executor"
        if any(word in text for word in ["browser", "open", "preview", "launch"]):
            return "browser"
        if any(word in text for word in ["screen", "screenshot", "vision", "look at"]):
            return "vision"
        if any(word in text for word in ["notepad", "desktop app", "calculator", "type text", "requested typing"]):
            return "desktop"
        if any(word in text for word in ["file", "folder", "write", "read", "inspect", "create", "edit", "apply", "implementation"]):
            return "filesystem"
        return None

    def _build_parameters(self, goal: str, step: PlanStep, tool_name: str | None, workspace_root: Path) -> dict:
        text = f"{step.title} {step.description}".lower()
        if tool_name == "filesystem":
            if any(word in text for word in ["inspect", "read", "list", "prepare", "identify"]):
                return {"operation": "list", "path": str(self.project_root or workspace_root)}
            if self._is_website_goal(goal) and any(word in text for word in ["apply", "implementation", "write", "create"]):
                output_path = website_output_path(goal, self.project_root or workspace_root)
                return {
                    "operation": "write",
                    "path": str(output_path),
                    "content": build_interactive_website_html(goal),
                }
            return {
                "operation": "write",
                "path": str(workspace_root / "generated_files" / "agent_note.md"),
                "content": f"# Lily Agent Note\n\nGoal: {goal}\n\nStep: {step.title}\n",
            }
        if tool_name == "browser":
            if self._is_website_goal(goal) and not self._is_external_browser_goal(goal):
                output_path = website_output_path(goal, self.project_root or workspace_root)
                return {"operation": "open", "path": str(output_path)}
            return {"operation": "open", "url": self._browser_url(goal)}
        if tool_name == "desktop":
            return self._desktop_parameters(goal)
        if tool_name == "vision":
            return {"operation": "analyze_screen"}
        if tool_name == "terminal":
            if "verify" in text or "compile" in text:
                if self._is_desktop_goal(goal) or self._is_external_browser_goal(goal) or self._is_screen_vision_goal(goal):
                    return {"command": "cmd /c exit 0", "cwd": str(self.project_root or workspace_root), "timeout": 10}
                if self._is_website_goal(goal):
                    output_path = website_output_path(goal, self.project_root or workspace_root)
                    command = (
                        "python -c "
                        f"\"from pathlib import Path; p=Path(r'{output_path}'); "
                        "text=p.read_text(encoding='utf-8'); "
                        "assert p.exists() and '<script>' in text and '<style>' in text; "
                        "print('Verified website:', p)\""
                    )
                    return {"command": command, "cwd": str(self.project_root or workspace_root), "timeout": 30}
                return {"command": "python -m compileall .", "cwd": str(self.project_root or workspace_root), "timeout": 60}
            return {"command": "dir" if self._is_windows() else "ls", "timeout": 30}
        if tool_name == "search":
            return {"query": goal, "force": True}
        if tool_name == "git":
            return {"operation": "status"}
        if tool_name == "python_executor":
            return {"code": "print('Lily python executor ready')", "timeout": 10}
        return {}

    def _desktop_parameters(self, goal: str) -> dict:
        lower = goal.lower()
        app = "notepad" if "notepad" in lower else "calculator" if "calculator" in lower or "calc" in lower else ""
        text = self._extract_type_text(goal)
        if app and text:
            return {"operation": "open_and_type", "app": app, "text": text}
        if app:
            return {"operation": "open_app", "app": app}
        if text:
            return {"operation": "type_text", "text": text}
        return {"operation": "open_app", "app": app}

    def _extract_type_text(self, goal: str) -> str:
        match = __import__("re").search(
            r"(?:type|write|enter)\s+(.+?)(?:\s+in\s+notepad|\s+into\s+notepad|\s+on\s+notepad)?[.!]?$",
            goal,
            __import__("re").IGNORECASE,
        )
        if not match:
            return ""
        text = match.group(1).strip().strip("\"'")
        return text[:1000]

    @staticmethod
    def _is_windows() -> bool:
        return "\\" in str(Path.cwd())

    @staticmethod
    def _is_website_goal(goal: str) -> bool:
        lower = goal.lower()
        return any(word in lower for word in ["website", "web app", "web page", "landing page", "interactive ui", "site"])

    @staticmethod
    def _is_desktop_goal(goal: str) -> bool:
        lower = goal.lower()
        return any(word in lower for word in ["notepad", "calculator", "desktop app", "type text"])

    @staticmethod
    def _is_screen_vision_goal(goal: str) -> bool:
        lower = goal.lower()
        return any(phrase in lower for phrase in ["see my screen", "look at my screen", "what is on my screen", "screenshot", "analyze my screen"])

    @staticmethod
    def _is_external_browser_goal(goal: str) -> bool:
        lower = goal.lower()
        return any(word in lower for word in ["youtube", "google", "browser", "http://", "https://", ".com", ".in", ".org", ".net"])

    def _browser_url(self, goal: str) -> str:
        lower = goal.lower()
        if "youtube" in lower:
            return "https://www.youtube.com/"
        if "google" in lower:
            return "https://www.google.com/"
        match = __import__("re").search(r"https?://[^\s]+", goal)
        if match:
            return match.group(0)
        domain = __import__("re").search(r"\b([a-z0-9-]+\.(?:com|in|org|net|ai|io|dev))\b", lower)
        if domain:
            return "https://" + domain.group(1)
        return "https://www.google.com/search?q=" + __import__("urllib.parse").parse.quote_plus(goal)

    def _mentions_live_search(self, text: str) -> bool:
        if "website" in text or "web app" in text:
            return False
        return bool(__import__("re").search(r"\b(search|web|latest|current|today|recent|news)\b", text))
