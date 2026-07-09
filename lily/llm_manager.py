"""Streaming LLM manager for Gemma4 with conversation context."""

from __future__ import annotations

import threading
from typing import Any

from lily.event_bus import EventBus, EventTypes


class LLMManager:
    """Manages streaming LLM responses with memory and location awareness."""

    def __init__(
        self,
        event_bus: EventBus,
        model: str = "gemma4:cloud",
        max_context_messages: int = 6,
    ):
        self.event_bus = event_bus
        self.model = model
        self.max_context_messages = max_context_messages
        self._ollama_available = False
        self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is available."""
        try:
            import ollama
            self._ollama_available = True
            print(f"[LLM] Ollama available with model: {self.model}")
        except ImportError:
            print("[LLM] Ollama not available")
            self.event_bus.publish(EventTypes.ERROR, {
                "source": "llm_manager",
                "error": "Ollama not installed"
            })

    def generate_stream(
        self,
        prompt: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ):
        """Generate streaming response from LLM.
        
        Yields events via event bus:
        - LLM_STARTED: When generation begins
        - LLM_TOKEN: For each token generated
        - LLM_FINISHED: When generation completes
        """
        if not self._ollama_available:
            yield {"error": "Ollama not available"}
            return

        try:
            import ollama
        except ImportError:
            yield {"error": "Ollama not installed"}
            return

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-self.max_context_messages:])
        
        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        # Default options for conversational responses
        default_options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 2048,
            "num_predict": 150,
            "keep_alive": "15m",
        }
        if options:
            default_options.update(options)

        # Emit start event
        self.event_bus.publish(EventTypes.LLM_STARTED, {
            "prompt": prompt,
            "model": self.model,
        })

        try:
            # Stream tokens
            full_response = []
            stream = ollama.chat(
                model=self.model,
                messages=messages,
                options=default_options,
                stream=True,
            )

            for chunk in stream:
                token = (chunk.get("message") or {}).get("content", "")
                if token:
                    full_response.append(token)
                    self.event_bus.publish(EventTypes.LLM_TOKEN, {"token": token})
                    yield {"token": token}

            # Emit finish event
            complete_response = "".join(full_response).strip()
            self.event_bus.publish(EventTypes.LLM_FINISHED, {
                "response": complete_response,
                "prompt": prompt,
            })
            
            yield {"response": complete_response, "done": True}

        except Exception as e:
            error_msg = f"LLM generation error: {e}"
            print(f"[LLM] {error_msg}")
            self.event_bus.publish(EventTypes.ERROR, {
                "source": "llm_manager",
                "error": error_msg,
            })
            yield {"error": error_msg}

    def generate_sync(
        self,
        prompt: str,
        system_prompt: str = "",
        conversation_history: list[dict[str, str]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> str:
        """Generate non-streaming response (for quick queries)."""
        if not self._ollama_available:
            return "[Ollama not available]"

        try:
            import ollama
        except ImportError:
            return "[Ollama not installed]"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if conversation_history:
            messages.extend(conversation_history[-self.max_context_messages:])
        
        messages.append({"role": "user", "content": prompt})

        default_options = {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 2048,
            "num_predict": 150,
        }
        if options:
            default_options.update(options)

        try:
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options=default_options,
            )
            return (response.get("message") or {}).get("content", "").strip()
        except Exception as e:
            print(f"[LLM] Sync generation error: {e}")
            return f"[Error: {e}]"

    def build_system_prompt(
        self,
        user_name: str = "Guest",
        location: str = "unknown",
        facts: list[str] | None = None,
        topics: list[str] | None = None,
        recalls: list[str] | None = None,
    ) -> str:
        """Build comprehensive system prompt with context."""
        
        facts_text = ""
        if facts:
            facts_text = "\n" + "\n".join(f"- {fact}" for fact in facts)
        
        topics_text = ""
        if topics:
            topics_text = f"\nRecent topics: {', '.join(topics)}"
        
        recalls_text = ""
        if recalls:
            recalls_text = f"\nRecent recalls: {', '.join(recalls)}"

        return f"""You are LILY, a warm, intelligent personal AI assistant.
You are currently speaking with {user_name}.

PERSONALITY & STYLE (CRITICAL):
- Default to SHORT, conversational answers: 1-2 sentences, under 40 words
- Sound friendly, natural, and slightly playful — never robotic
- NO emojis, NO bullet lists, NO markdown unless explicitly asked
- Only give detailed answers when user clearly wants depth
- Skip filler phrases — jump straight to the point

CURRENT LOCATION: {location}
Use location naturally only when relevant.

WHAT YOU KNOW ABOUT {user_name}:{facts_text or "\n(Learning about them...)"}
{topics_text}
{recalls_text}

CAPABILITIES (mention only if asked):
- Live camera view
- Smart web search for current info
- Tool execution for computer tasks
- Memory and learning

Keep responses conversational and concise by default."""
