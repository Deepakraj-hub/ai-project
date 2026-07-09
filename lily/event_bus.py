"""Thread-safe event bus for Lily's streaming voice architecture."""

from __future__ import annotations

import queue
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable


class EventTypes:
    AUDIO_CHUNK = "AUDIO_CHUNK"
    USER_STARTED_SPEAKING = "USER_STARTED_SPEAKING"
    USER_STOPPED_SPEAKING = "USER_STOPPED_SPEAKING"
    TRANSCRIPT_PARTIAL = "TRANSCRIPT_PARTIAL"
    TRANSCRIPT_READY = "TRANSCRIPT_READY"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_FINISHED = "TOOL_FINISHED"
    TOOL_REQUEST = "TOOL_REQUEST"
    LLM_STARTED = "LLM_STARTED"
    LLM_TOKEN = "LLM_TOKEN"
    LLM_SENTENCE = "LLM_SENTENCE"
    LLM_FINISHED = "LLM_FINISHED"
    TTS_STARTED = "TTS_STARTED"
    TTS_STOPPED = "TTS_STOPPED"
    TTS_INTERRUPTED = "TTS_INTERRUPTED"
    MEMORY_SAVED = "MEMORY_SAVED"
    STATE_CHANGED = "STATE_CHANGED"
    ERROR = "ERROR"
    ALL = "*"


@dataclass(frozen=True)
class Event:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


Handler = Callable[[Event], None]


class EventBus:
    """Small pub/sub hub used by managers and the UI boundary."""

    def __init__(self):
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, handler: Handler) -> Callable[[], None]:
        with self._lock:
            self._subscribers[event_type].append(handler)

        def unsubscribe():
            with self._lock:
                handlers = self._subscribers.get(event_type, [])
                if handler in handlers:
                    handlers.remove(handler)

        return unsubscribe

    def queue_for(self, event_type: str, maxsize: int = 0) -> queue.Queue:
        events = queue.Queue(maxsize=maxsize)
        self.subscribe(event_type, events.put)
        return events

    def publish(self, event_type: str, payload: dict[str, Any] | None = None) -> Event:
        event = Event(event_type, payload or {})
        with self._lock:
            handlers = list(self._subscribers.get(event_type, ()))
            handlers.extend(self._subscribers.get(EventTypes.ALL, ()))

        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:
                if event_type != EventTypes.ERROR:
                    self.publish(EventTypes.ERROR, {"source": event_type, "error": str(exc)})
        return event
