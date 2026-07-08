"""Gemma provider alias for the configured Ollama/cloud model."""

from __future__ import annotations

from lily.models.ollama import OllamaProvider


class GemmaProvider(OllamaProvider):
    name = "gemma"
