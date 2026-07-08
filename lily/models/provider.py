"""Provider-neutral model interface."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class ModelResponse:
    text: str
    raw: dict | None = None


class ModelProvider(Protocol):
    """Protocol for all Lily model providers."""

    name: str

    def complete(self, messages: list[dict], options: dict | None = None) -> ModelResponse:
        """Return a text completion for chat-style messages."""
