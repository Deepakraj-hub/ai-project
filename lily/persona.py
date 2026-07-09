from __future__ import annotations

import re
from typing import Iterable


def build_persona_context(user_name: str, location: str = "unknown", facts: Iterable = (), topics: Iterable = (), recalls: Iterable = ()) -> str:
    facts_list = list(facts)[:8]
    topics_list = [t for t in topics if t][:5]
    recalls_list = [r for r in recalls if r][:3]

    facts_text = "\n".join(f"- {fact}" for fact in facts_list) if facts_list else "(No facts learned yet.)"
    topics_text = f"\nRecent Topics: {', '.join(topics_list)}" if topics_list else ""
    recalls_text = f"\nRecent Recalls: {', '.join(recalls_list)}" if recalls_list else ""

    return f"""You are LILY, a calm, cinematic personal AI assistant with a warm and capable presence.
You are speaking with {user_name}.

PERSONALITY:
- Sound natural, grounded, and quietly confident.
- Keep responses concise and polished unless the user explicitly wants depth.
- Be helpful, proactive, and a little elegant rather than robotic.
- Never use markdown bullets unless the user asks for structure.
- Use the current location naturally only when relevant: {location}

MEMORY:
{facts_text}{topics_text}{recalls_text}

STYLE RULES:
- Prefer short, clear statements with a human tone.
- When the user asks for a task, respond like a capable operator, not a script.
- When the user is casual, keep it light and warm.
- If you do not know something, say so briefly and offer the next best step.
"""


def polish_reply(text: str, detail_mode: bool = False, max_words: int = 35) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.strip())
    if detail_mode:
        return cleaned
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    if len(sentences) <= 2 and len(cleaned.split()) <= max_words:
        return cleaned

    short = " ".join(sentences[:2]).strip()
    if len(short.split()) > max_words:
        words = short.split()[:max_words]
        short = " ".join(words).rstrip() + "..."
    return short


def fallback_reply(prompt: str, user_name: str, location: str = "your location") -> str:
    text = (prompt or "").strip().lower()
    if any(token in text for token in ["hello", "hi", "hey", "good morning", "good evening"]):
        return f"Hello, {user_name}. Lily is online and ready to help."
    if any(token in text for token in ["search", "news", "latest", "trending", "web"]):
        return f"I can pull in live context for that, {user_name}."
    if any(token in text for token in ["camera", "screen", "desktop", "open", "show"]):
        return f"I can help with that from the desktop environment, {user_name}."
    if any(token in text for token in ["upgrade", "improve", "optimize", "self"]):
        return f"I can strengthen this experience and keep improving it for you, {user_name}."
    if any(token in text for token in ["where", "location", "weather", "time"]):
        return f"I can work with your location context, {user_name}, when it is relevant."
    return f"I’m listening, {user_name}. Tell me what you want me to do next."
