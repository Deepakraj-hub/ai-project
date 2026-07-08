"""Ollama model provider."""

from __future__ import annotations

from lily.models.provider import ModelResponse


class OllamaProvider:
    name = "ollama"

    def __init__(self, model: str = "gemma4:cloud"):
        self.model = model

    def complete(self, messages: list[dict], options: dict | None = None) -> ModelResponse:
        try:
            import ollama
        except ImportError as exc:
            raise RuntimeError("Ollama is not installed.") from exc
        response = ollama.chat(model=self.model, messages=messages, options=options or {})
        text = (response.get("message") or {}).get("content", "").strip()
        return ModelResponse(text=text, raw=response)
