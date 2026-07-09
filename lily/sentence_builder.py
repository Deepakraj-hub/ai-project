"""Streaming sentence builder that collects LLM tokens into complete sentences."""

from __future__ import annotations

import queue
import re
import threading
from collections import deque

from lily.event_bus import EventBus, EventTypes


class SentenceBuilder:
    """Collects streaming tokens and emits complete sentences for TTS."""

    SENTENCE_TERMINATORS = r'[.!?;]\s*$'
    PAUSE_MARKERS = r'[,]\s*$'
    
    def __init__(self, event_bus: EventBus, min_sentence_length: int = 15):
        self.event_bus = event_bus
        self.min_sentence_length = min_sentence_length
        self._buffer = ""
        self._lock = threading.Lock()
        self._running = False
        self._unsubs = [
            event_bus.subscribe(EventTypes.LLM_TOKEN, self._on_token),
            event_bus.subscribe(EventTypes.LLM_FINISHED, self._on_finished),
        ]

    def start(self):
        """Start the sentence builder."""
        self._running = True
        with self._lock:
            self._buffer = ""

    def close(self):
        """Stop and clean up."""
        self._running = False
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_token(self, event):
        """Accumulate tokens and emit sentences when complete."""
        if not self._running:
            return
            
        token = event.payload.get("token", "")
        if not token:
            return

        with self._lock:
            self._buffer += token
            
            # Check if we have a complete sentence
            if len(self._buffer) >= self.min_sentence_length:
                if re.search(self.SENTENCE_TERMINATORS, self._buffer):
                    sentence = self._buffer.strip()
                    self._buffer = ""
                    self.event_bus.publish(EventTypes.LLM_SENTENCE, {"sentence": sentence})
                    return
                    
                # Also emit on commas if buffer is getting long (for more natural flow)
                if len(self._buffer) > 80 and re.search(self.PAUSE_MARKERS, self._buffer):
                    sentence = self._buffer.strip()
                    self._buffer = ""
                    self.event_bus.publish(EventTypes.LLM_SENTENCE, {"sentence": sentence})

    def _on_finished(self, event):
        """Emit any remaining buffered text."""
        with self._lock:
            if self._buffer.strip():
                sentence = self._buffer.strip()
                self._buffer = ""
                self.event_bus.publish(EventTypes.LLM_SENTENCE, {"sentence": sentence})
