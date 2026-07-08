"""OpenAI provider placeholder."""

from __future__ import annotations

from lily.models.provider import ModelResponse


class OpenAIProvider:
    name = "openai"

    def complete(self, messages: list[dict], options: dict | None = None) -> ModelResponse:
        raise RuntimeError("OpenAI provider is not configured yet.")
