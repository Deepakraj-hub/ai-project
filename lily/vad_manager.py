"""Voice activity detection manager.

Silero VAD can be plugged in when installed. The default path is a fast RMS
fallback so Lily still works on a fresh local setup.
"""

from __future__ import annotations

import threading
import time

import numpy as np

from lily.event_bus import Event, EventBus, EventTypes


class VADManager:
    """Publishes user speaking/silent events from audio chunks."""

    def __init__(
        self,
        event_bus: EventBus,
        speech_threshold: float = 300.0,
        silence_timeout: float = 0.7,
        barge_in_threshold: float = 900.0,
    ):
        self.event_bus = event_bus
        self.speech_threshold = speech_threshold
        self.silence_timeout = silence_timeout
        self.barge_in_threshold = barge_in_threshold
        self._speaking = False
        self._lily_speaking = False
        self._last_voice_at = 0.0
        self._lock = threading.Lock()
        self._unsubs = [
            event_bus.subscribe(EventTypes.AUDIO_CHUNK, self._on_audio_chunk),
            event_bus.subscribe(EventTypes.TTS_STARTED, self._on_tts_started),
            event_bus.subscribe(EventTypes.TTS_STOPPED, self._on_tts_stopped),
        ]

    def close(self):
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_tts_started(self, event: Event):
        with self._lock:
            self._lily_speaking = True

    def _on_tts_stopped(self, event: Event):
        with self._lock:
            self._lily_speaking = False

    def _on_audio_chunk(self, event: Event):
        chunk = event.payload.get("chunk")
        if not chunk:
            return
        volume = float(np.abs(chunk.samples).mean())
        now = time.monotonic()

        with self._lock:
            lily_speaking = self._lily_speaking
            was_speaking = self._speaking

            if volume > self.speech_threshold:
                self._last_voice_at = now
                self._speaking = True
            elif self._speaking and now - self._last_voice_at > self.silence_timeout:
                self._speaking = False

            is_speaking = self._speaking

        if is_speaking and not was_speaking:
            self.event_bus.publish(EventTypes.USER_STARTED_SPEAKING, {"volume": volume})
        elif was_speaking and not is_speaking:
            self.event_bus.publish(EventTypes.USER_STOPPED_SPEAKING, {"volume": volume})

        if lily_speaking and volume > self.barge_in_threshold:
            self.event_bus.publish(EventTypes.TTS_INTERRUPTED, {"reason": "barge_in", "volume": volume})
