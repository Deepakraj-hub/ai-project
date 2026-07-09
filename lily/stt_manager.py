"""Streaming speech-to-text manager using Whisper."""

from __future__ import annotations

import queue
import threading
import time
from collections import deque

import numpy as np

from lily.event_bus import EventBus, EventTypes


class STTManager:
    """Streaming Whisper transcription with partial and final outputs."""

    def __init__(
        self,
        event_bus: EventBus,
        model_size: str = "base",
        sample_rate: int = 16000,
        chunk_duration: float = 2.0,
    ):
        self.event_bus = event_bus
        self.model_size = model_size
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self._model = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._audio_buffer = deque(maxlen=int(sample_rate * 10))  # 10 sec buffer
        self._lock = threading.Lock()
        self._last_transcript = ""
        self._unsubs = [
            event_bus.subscribe(EventTypes.USER_STARTED_SPEAKING, self._on_user_started),
            event_bus.subscribe(EventTypes.USER_STOPPED_SPEAKING, self._on_user_stopped),
            event_bus.subscribe(EventTypes.AUDIO_CHUNK, self._on_audio_chunk),
        ]

    def start(self):
        """Initialize Whisper model and start processing thread."""
        if self._running:
            return
        try:
            import whisper
            self._model = whisper.load_model(self.model_size)
            print(f"[STT] Whisper model '{self.model_size}' loaded")
        except Exception as e:
            print(f"[STT] Failed to load Whisper: {e}")
            self.event_bus.publish(EventTypes.ERROR, {"source": "stt_manager", "error": str(e)})
            return

        self._running = True
        self._thread = threading.Thread(target=self._transcription_loop, daemon=True)
        self._thread.start()

    def close(self):
        """Stop processing and clean up."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_user_started(self, event):
        """Clear buffer when user starts speaking."""
        with self._lock:
            self._audio_buffer.clear()
            self._last_transcript = ""

    def _on_user_stopped(self, event):
        """Trigger final transcription when user stops."""
        self.event_bus.publish(EventTypes.TRANSCRIPT_PARTIAL, {"text": "", "final": True})

    def _on_audio_chunk(self, event):
        """Accumulate audio chunks for transcription."""
        chunk = event.payload.get("chunk")
        if not chunk or not self._running:
            return
        with self._lock:
            # Convert int16 to float32 normalized audio
            audio_float = chunk.samples.flatten().astype(np.float32) / 32768.0
            self._audio_buffer.extend(audio_float)

    def _transcription_loop(self):
        """Continuously transcribe accumulated audio."""
        import whisper

        while self._running:
            time.sleep(self.chunk_duration)
            
            with self._lock:
                if len(self._audio_buffer) < self.sample_rate * 0.5:  # Need at least 0.5s
                    continue
                audio_array = np.array(list(self._audio_buffer), dtype=np.float32)

            try:
                # Pad or trim to 30 seconds (Whisper requirement)
                audio_padded = whisper.pad_or_trim(audio_array)
                
                # Transcribe
                result = self._model.transcribe(
                    audio_padded,
                    language="en",
                    task="transcribe",
                    fp16=False,
                    verbose=False,
                )
                
                text = result.get("text", "").strip()
                
                if text and text != self._last_transcript:
                    self._last_transcript = text
                    # Emit partial transcript
                    self.event_bus.publish(EventTypes.TRANSCRIPT_PARTIAL, {
                        "text": text,
                        "final": False,
                    })
                    
            except Exception as e:
                print(f"[STT] Transcription error: {e}")
                continue

    def transcribe_final(self) -> str:
        """Get final transcription of accumulated audio."""
        if not self._model:
            return ""
            
        with self._lock:
            if len(self._audio_buffer) == 0:
                return ""
            audio_array = np.array(list(self._audio_buffer), dtype=np.float32)

        try:
            import whisper
            audio_padded = whisper.pad_or_trim(audio_array)
            result = self._model.transcribe(
                audio_padded,
                language="en",
                task="transcribe",
                fp16=False,
            )
            text = result.get("text", "").strip()
            
            if text:
                self.event_bus.publish(EventTypes.TRANSCRIPT_READY, {"text": text})
                self._last_transcript = ""
                return text
                
        except Exception as e:
            print(f"[STT] Final transcription error: {e}")
            
        return ""
