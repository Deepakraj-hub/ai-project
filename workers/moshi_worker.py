"""
MoshiVoiceWorker - simulated duplex voice input with barge-in detection.

It still tries a local Moshi server first, but the fallback no longer stops the
microphone while Lily speaks. Instead it watches for a louder user speech spike
and emits interrupt_requested so the UI can stop generation and playback.
"""

import asyncio
import json
import threading
import time
import traceback

import numpy as np
from PySide6.QtCore import QThread, Signal


class MoshiVoiceWorker(QThread):
    status_changed = Signal(str)
    user_speech = Signal(str)
    interrupt_requested = Signal()
    error = Signal(str)

    SAMPLE_RATE = 16000
    BLOCK_DURATION = 0.1
    SILENCE_THRESHOLD = 300
    BARGE_IN_THRESHOLD = 900
    BARGE_IN_BLOCKS = 3
    INTERRUPT_COOLDOWN_SECS = 0.8
    SILENCE_TIMEOUT_SECS = 1.2
    MAX_PHRASE_SECS = 15

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._speaking = False
        self._state_lock = threading.Lock()
        self._last_interrupt_at = 0.0

    def pause(self):
        self.set_lily_speaking(True)

    def resume(self):
        self.set_lily_speaking(False)

    def set_lily_speaking(self, speaking: bool):
        with self._state_lock:
            self._speaking = speaking

    @property
    def is_speaking(self):
        with self._state_lock:
            return self._speaking

    def _maybe_emit_interrupt(self):
        now = time.monotonic()
        if now - self._last_interrupt_at < self.INTERRUPT_COOLDOWN_SECS:
            return
        self._last_interrupt_at = now
        self.status_changed.emit("● INTERRUPTING")
        self.interrupt_requested.emit()

    def run(self):
        self._running = True
        self.status_changed.emit("● CONNECTING TO MOSHI")

        ws_connected = False
        try:
            import websockets
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def test_ws():
                async with websockets.connect("ws://localhost:8998/api/chat", ping_timeout=2) as ws:
                    return True

            try:
                time.sleep(3)
                ws_connected = loop.run_until_complete(asyncio.wait_for(test_ws(), timeout=2.0))
            except Exception:
                ws_connected = False
            finally:
                loop.close()
        except ImportError:
            print("[LILY] websockets package not found. Skipping true Moshi connection.")

        if ws_connected:
            self.status_changed.emit("● TRUE MOSHI CONNECTED")
            self._run_true_moshi()
        else:
            print("[LILY] Moshi server not available. Falling back to simulated duplex.")
            self._run_simulated_moshi()

    def _run_true_moshi(self):
        """Runs the actual Kyutai Moshi WebSocket client when available."""
        import websockets

        async def true_moshi_loop():
            async with websockets.connect("ws://localhost:8998/api/chat") as ws:
                while self._running:
                    message = await ws.recv()
                    data = json.loads(message)
                    text = data.get("text")
                    if text:
                        self.user_speech.emit(text)

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(true_moshi_loop())
        except Exception as e:
            print(f"[True Moshi Error] {e}")
            self._run_simulated_moshi()

    def _run_simulated_moshi(self):
        """Falls back to local speech recognition while keeping the mic live."""
        self.status_changed.emit("● DUPLEX ACTIVE")
        try:
            import sounddevice as sd
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            block_size = int(self.SAMPLE_RATE * self.BLOCK_DURATION)
            silence_blocks_needed = int(self.SILENCE_TIMEOUT_SECS / self.BLOCK_DURATION)
            max_blocks = int(self.MAX_PHRASE_SECS / self.BLOCK_DURATION)

            while self._running:
                self.status_changed.emit("● LISTENING")

                recorded_blocks = []
                speech_started = False
                silence_run = 0
                block_count = 0
                barge_blocks = 0

                try:
                    with sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1,
                                        dtype="int16", blocksize=block_size) as stream:
                        while self._running:
                            block, _ = stream.read(block_size)
                            block_count += 1

                            volume = np.abs(block).mean()
                            if self.is_speaking and volume > self.BARGE_IN_THRESHOLD:
                                barge_blocks += 1
                                if barge_blocks >= self.BARGE_IN_BLOCKS:
                                    self._maybe_emit_interrupt()
                                    barge_blocks = 0
                            elif volume <= self.BARGE_IN_THRESHOLD:
                                barge_blocks = 0

                            if volume > self.SILENCE_THRESHOLD:
                                speech_started = True
                                silence_run = 0
                                recorded_blocks.append(block.copy())
                            elif speech_started:
                                recorded_blocks.append(block.copy())
                                silence_run += 1
                                if silence_run >= silence_blocks_needed:
                                    break

                            if block_count > max_blocks:
                                break
                except Exception as e:
                    print(f"[Moshi Mic Error] {e}")
                    time.sleep(0.5)
                    continue

                if not speech_started or not recorded_blocks:
                    continue

                self.status_changed.emit("● PROCESSING")

                try:
                    audio_np = np.concatenate(recorded_blocks, axis=0)
                    audio_bytes = audio_np.tobytes()
                    audio_data = sr.AudioData(audio_bytes, self.SAMPLE_RATE, 2)
                    text = recognizer.recognize_google(audio_data)
                    if text and text.strip():
                        self.user_speech.emit(text.strip())
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    print(f"[Moshi SR Error] {e}")
                except Exception as e:
                    print(f"[Moshi Transcribe Error] {e}")

        except ImportError as e:
            self.error.emit(f"Missing audio library: {e}")
        except Exception as e:
            traceback.print_exc()
            self.error.emit(f"Moshi Error: {str(e)}")
        finally:
            self._running = False
            self.status_changed.emit("○ IDLE")

    def stop(self):
        self._running = False
        self.quit()
        self.wait(3000)
