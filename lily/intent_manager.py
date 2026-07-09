"""Fast rule-based intent classification for Lily voice commands."""

from __future__ import annotations

from dataclasses import dataclass

from lily.event_bus import EventBus, EventTypes


@dataclass(frozen=True)
class Intent:
    kind: str
    confidence: float
    text: str


class IntentKinds:
    CONVERSATION = "conversation"
    TOOL = "tool"


class IntentManager:
    """Classifies transcript text before routing to Gemma or Hermes."""

    TOOL_PREFIXES = ("agent ", "task ")
    TOOL_VERBS = (
        "open", "close", "launch", "go", "visit", "click", "type", "move",
        "create", "make", "build", "develop", "design", "generate", "write",
        "fix", "refactor", "test", "run", "analyze", "review", "summarize",
        "organize", "convert", "send", "email", "search", "download",
    )
    TOOL_OBJECTS = (
        "chrome", "browser", "youtube", "google", "website", "web app",
        "file", "folder", "desktop", "window", "screen", "screenshot",
        "notepad", "calculator", "email", "pdf", "document", "project",
        "app", "script", "terminal",
    )

    def __init__(self, event_bus: EventBus | None = None):
        self.event_bus = event_bus

    def classify(self, text: str) -> Intent:
        lower = (text or "").lower().strip()
        if not lower:
            intent = Intent(IntentKinds.CONVERSATION, 0.0, text)
        elif lower.startswith(self.TOOL_PREFIXES):
            intent = Intent(IntentKinds.TOOL, 0.95, text)
        elif any(phrase in lower for phrase in (
            "see my screen", "look at my screen", "take a screenshot",
            "capture my screen", "open youtube", "go to youtube",
        )):
            intent = Intent(IntentKinds.TOOL, 0.9, text)
        elif any(lower.startswith(verb + " ") for verb in self.TOOL_VERBS) and any(
            obj in lower for obj in self.TOOL_OBJECTS
        ):
            intent = Intent(IntentKinds.TOOL, 0.82, text)
        else:
            intent = Intent(IntentKinds.CONVERSATION, 0.75, text)

        if self.event_bus:
            self.event_bus.publish(EventTypes.INTENT_CLASSIFIED, {
                "kind": intent.kind,
                "confidence": intent.confidence,
                "text": intent.text,
            })
        return intent
