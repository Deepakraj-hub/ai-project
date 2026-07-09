"""Streaming TTS manager with interruption support using Edge TTS."""

from __future__ import annotations

import asyncio
import os
import queue
import tempfile
import threading
import time

from lily.event_bus import EventBus, EventTypes


class TTSManager:
    """Streaming text-to-speech with barge-in interruption."""

    def __init__(self, event_bus: EventBus, voice: str = "en-US-AvaMultilingualNeural"):
        self.event_bus = event_bus
        self.voice = voice
        self._sentence_queue: queue.Queue[str | None] = queue.Queue()
        self._interrupt_event = threading.Event()
        self._speaking = False
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._unsubs = [
            event_bus.subscribe(EventTypes.LLM_SENTENCE, self._on_sentence),
            event_bus.subscribe(EventTypes.TTS_INTERRUPTED, self._on_interrupt),
        ]

    def start(self):
        """Start the TTS processing thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._tts_loop, daemon=True)
        self._thread.start()

    def close(self):
        """Stop processing and clean up."""
        self._running = False
        self._sentence_queue.put(None)  # Signal thread to stop
        if self._thread:
            self._thread.join(timeout=2.0)
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    def _on_sentence(self, event):
        """Queue sentences for speaking."""
        sentence = event.payload.get("sentence", "")
        if sentence:
            self._sentence_queue.put(sentence)

    def _on_interrupt(self, event):
        """Handle barge-in interruption."""
        self._interrupt_event.set()
        with self._lock:
            # Clear pending sentences
            while not self._sentence_queue.empty():
                try:
                    self._sentence_queue.get_nowait()
                except queue.Empty:
                    break

    def stop_speaking(self):
        """Immediately stop current speech."""
        self._interrupt_event.set()

    def _tts_loop(self):
        """Main TTS processing loop."""
        while self._running:
            try:
                # Wait for next sentence
                sentence = self._sentence_queue.get(timeout=0.5)
                if sentence is None:  # Stop signal
                    break
                    
                # Clear interrupt flag
                self._interrupt_event.clear()
                
                # Speak the sentence
                self._speak_sentence(sentence)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[TTS] Error: {e}")
                self.event_bus.publish(EventTypes.ERROR, {"source": "tts_manager", "error": str(e)})

    def _speak_sentence(self, text: str):
        """Synthesize and play a single sentence."""
        if not text.strip():
            return

        with self._lock:
            self._speaking = True
        
        self.event_bus.publish(EventTypes.TTS_STARTED, {"text": text})
        
        try:
            # Run async TTS in sync context
            asyncio.run(self._async_speak(text))
        except Exception as e:
            print(f"[TTS] Speech synthesis error: {e}")
        finally:
            with self._lock:
                self._speaking = False
            self.event_bus.publish(EventTypes.TTS_STOPPED, {"text": text})

    async def _async_speak(self, text: str):
        """Async TTS synthesis and playback with interruption support."""
        try:
            import edge_tts
            import sounddevice as sd
            import soundfile as sf
            from lily.voice import save_speech
        except ImportError as e:
            print(f"[TTS] Missing dependencies: {e}")
            return

        # Generate speech file
        temp_file = tempfile.mktemp(suffix=".mp3")
        try:
            await save_speech(edge_tts, text, temp_file)
            
            # Load audio
            data, samplerate = sf.read(temp_file, dtype="float32")
            
            # Play with interruption check
            chunk_size = int(samplerate * 0.1)  # 100ms chunks
            for i in range(0, len(data), chunk_size):
                if self._interrupt_event.is_set():
                    sd.stop()
                    break
                    
                chunk = data[i:i + chunk_size]
                sd.play(chunk, samplerate)
                sd.wait()
                
        finally:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass
