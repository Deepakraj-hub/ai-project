"""Shared voice profile for Lily text-to-speech."""

from __future__ import annotations

import os
import re


# Natural female voices. The first one is preferred; the rest are fallbacks
# in case a local Edge TTS install does not expose the newest voice.
VOICE_CANDIDATES = [
    os.getenv("LILY_VOICE", "en-US-AvaMultilingualNeural"),
    "en-US-AriaNeural",
    "en-US-JennyNeural",
]

VOICE_RATE = os.getenv("LILY_VOICE_RATE", "-6%")
VOICE_PITCH = os.getenv("LILY_VOICE_PITCH", "+3Hz")
VOICE_VOLUME = os.getenv("LILY_VOICE_VOLUME", "+0%")


def clean_for_speech(text: str) -> str:
    """Remove UI/markdown clutter so TTS sounds more conversational."""

    cleaned = text or ""
    cleaned = re.sub(r"https?://\S+", "I opened the link for you.", cleaned)
    cleaned = re.sub(r"[*_`#>\[\]{}|]", " ", cleaned)
    cleaned = re.sub(r"^[\s\-•✓✗]+", "", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:1200]


async def save_speech(edge_tts, text: str, filename: str) -> str:
    """Synthesize speech with the preferred voice and fallback if needed."""

    speech_text = clean_for_speech(text)
    last_error = None
    for voice in dict.fromkeys(VOICE_CANDIDATES):
        try:
            communicate = edge_tts.Communicate(
                text=speech_text,
                voice=voice,
                rate=VOICE_RATE,
                pitch=VOICE_PITCH,
                volume=VOICE_VOLUME,
            )
            await communicate.save(filename)
            return voice
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"No Lily voice could synthesize speech: {last_error}")
