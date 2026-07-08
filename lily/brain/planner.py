"""Goal decomposition for Lily's autonomous tasks."""

from __future__ import annotations

import json
import re

from lily.brain.schema import PlanStep, TaskPlan
from lily.models.provider import ModelProvider


class Planner:
    """Turns a user goal into an executable plan."""

    def __init__(self, model_provider: ModelProvider | None = None):
        self.model_provider = model_provider

    def create_plan(self, task_id: str, goal: str) -> TaskPlan:
        if self.model_provider:
            plan = self._model_plan(task_id, goal)
            if plan:
                return plan
        return self._heuristic_plan(task_id, goal)

    def _model_plan(self, task_id: str, goal: str) -> TaskPlan | None:
        prompt = (
            "Decompose this desktop AI agent goal into 3-8 concrete steps. "
            "Return only JSON: {\"steps\":[{\"title\":\"...\",\"description\":\"...\",\"tool_hint\":\"filesystem|terminal|search|git|python_executor|browser|desktop|vision|null\"}]}.\n"
            f"Goal: {goal}"
        )
        try:
            response = self.model_provider.complete([{"role": "user", "content": prompt}], {"temperature": 0.1})
            content = response.text.strip()
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
            payload = json.loads(content)
            steps = [
                PlanStep.create(
                    item.get("title", "Unnamed step"),
                    item.get("description", ""),
                    item.get("tool_hint"),
                )
                for item in payload.get("steps", [])
                if item.get("title")
            ]
            if steps:
                return TaskPlan(task_id=task_id, goal=goal, steps=steps)
        except Exception:
            return None
        return None

    def _heuristic_plan(self, task_id: str, goal: str) -> TaskPlan:
        lower = goal.lower()
        steps: list[PlanStep] = [PlanStep.create("Understand the goal", goal)]

        if any(word in lower for word in ["analyze", "summarize", "understand", "review"]):
            steps.append(PlanStep.create("Inspect relevant files", "Read project structure and important files.", "filesystem"))
        if self._needs_live_search(lower):
            steps.append(PlanStep.create("Gather live information", "Search the web for current supporting context.", "search"))
        if any(word in lower for word in ["build", "create", "edit", "refactor", "fix", "upgrade", "implement", "design", "develop", "make"]):
            steps.append(PlanStep.create("Prepare file changes", "Identify files to create or modify.", "filesystem"))
            steps.append(PlanStep.create("Apply implementation", "Write the required code or content.", "filesystem"))
        if any(word in lower for word in ["youtube", "google", "browser", "url", ".com", ".in", ".org", ".net"]):
            steps.append(PlanStep.create("Open browser page", "Open the requested website or URL in the browser.", "browser"))
        if any(word in lower for word in ["website", "web app", "web page", "landing page", "interactive"]):
            steps.append(PlanStep.create("Open finished preview", "Launch the built site in the default browser.", "browser"))
        if any(phrase in lower for phrase in ["see my screen", "look at my screen", "what is on my screen", "screenshot", "screen vision", "analyze my screen"]):
            steps.append(PlanStep.create("Inspect screen", "Capture and analyze the current screen.", "vision"))
        if any(word in lower for word in ["notepad", "calculator", "desktop", "open app", "type hello", "type text"]):
            steps.append(PlanStep.create("Operate desktop app", "Open the requested desktop application and perform the requested typing.", "desktop"))
        if any(word in lower for word in ["test", "run", "verify", "compile", "server"]):
            steps.append(PlanStep.create("Run verification", "Execute the relevant command and inspect output.", "terminal"))

        steps.append(PlanStep.create("Verify outcome", "Check whether the result satisfies the goal.", "terminal"))
        steps.append(PlanStep.create("Reflect and report", "Summarize actions, failures, and next improvements."))
        return TaskPlan(task_id=task_id, goal=goal, steps=steps)

    def _needs_live_search(self, lower_goal: str) -> bool:
        if "website" in lower_goal or "web app" in lower_goal:
            return False
        return bool(re.search(r"\b(latest|search|web|news|current|today|recent)\b", lower_goal))
