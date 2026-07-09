"""Microphone and speaker queues for Lily's streaming voice pipeline."""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass
from typing import Any

from lily.event_bus import EventBus, EventTypes


@dataclass(frozen=True)
class AudioChunk:
    samples: Any
    sample_rate: int
    timestamp: float


class AudioManager:
    """Owns audio queues and the long-running microphone capture loop."""

    def __init__(self, event_bus: EventBus, sample_rate: int = 16000, block_duration: float = 0.1):
        self.event_bus = event_bus
        self.sample_rate = sample_rate
        self.block_duration = block_duration
        self.mic_queue: queue.Queue[AudioChunk] = queue.Queue(maxsize=80)
        self.speaker_queue: queue.Queue[Any] = queue.Queue()
        self.interrupt_event = threading.Event()
        self._running = threading.Event()
        self._mic_thread: threading.Thread | None = None

    def start(self):
        if self._mic_thread and self._mic_thread.is_alive():
            return
        self._running.set()
        self._mic_thread = threading.Thread(target=self._mic_loop, daemon=True)
        self._mic_thread.start()

    def stop(self):
        self._running.clear()
        self.interrupt_event.set()
        if self._mic_thread:
            self._mic_thread.join(timeout=2.0)

    def _mic_loop(self):
        try:
            import sounddevice as sd

            block_size = int(self.sample_rate * self.block_duration)
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                blocksize=block_size,
            ) as stream:
                while self._running.is_set():
                    samples, _ = stream.read(block_size)
                    chunk = AudioChunk(samples=samples.copy(), sample_rate=self.sample_rate, timestamp=time.monotonic())
                    self._put_latest(self.mic_queue, chunk)
                    self.event_bus.publish(EventTypes.AUDIO_CHUNK, {"chunk": chunk})
        except Exception as exc:
            self.event_bus.publish(EventTypes.ERROR, {"source": "audio_manager", "error": str(exc)})

    @staticmethod
    def _put_latest(target: queue.Queue, item):
        try:
            target.put_nowait(item)
        except queue.Full:
            try:
                target.get_nowait()
            except queue.Empty:
                pass
            target.put_nowait(item)
