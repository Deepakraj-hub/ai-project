"""OpenRouter provider placeholder."""

from __future__ import annotations

from lily.models.provider import ModelResponse


class OpenRouterProvider:
    name = "openrouter"

    def complete(self, messages: list[dict], options: dict | None = None) -> ModelResponse:
        raise RuntimeError("OpenRouter provider is not configured yet.")
