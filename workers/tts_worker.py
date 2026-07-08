"""
TTSWorker — QThread wrapper for edge-tts text-to-speech.
Generates audio with edge-tts and plays it via sounddevice.
"""

import asyncio
import os
import tempfile

from PySide6.QtCore import QThread, Signal


class TTSWorker(QThread):
    """Runs edge-tts synthesis + playback on a background thread."""

    started_speaking = Signal()
    finished_speaking = Signal()
    error = Signal(str)

    VOICE = "en-US-AvaMultilingualNeural"

    def __init__(self, text, parent=None):
        super().__init__(parent)
        self._text = text

    def run(self):
        try:
            import edge_tts

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            filename = tempfile.mktemp(suffix=".mp3")
            from lily.voice import save_speech

            loop.run_until_complete(save_speech(edge_tts, self._text, filename))

            self.started_speaking.emit()

            try:
                import sounddevice as sd
                import soundfile as sf

                data, samplerate = sf.read(filename, dtype="float32")
                sd.play(data, samplerate)
                sd.wait()
            except ImportError:
                pass

            try:
                os.remove(filename)
            except Exception:
                pass

            loop.close()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished_speaking.emit()


class VoiceInputWorker(QThread):
    """Listens for voice input using SpeechRecognition on a background thread."""

    recognized = Signal(str)
    listening = Signal()
    stopped = Signal()
    error = Signal(str)

    SAMPLE_RATE = 16000
    BLOCK_DURATION = 0.1
    MAX_LISTEN_SECONDS = 10
    SILENCE_DURATION = 1.0
    SILENCE_THRESHOLD = 400

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False

    def run(self):
        self._running = True
        try:
            import numpy as np
            import sounddevice as sd
            import speech_recognition as sr

            self.listening.emit()

            block_size = int(self.SAMPLE_RATE * self.BLOCK_DURATION)
            max_blocks = int(self.MAX_LISTEN_SECONDS / self.BLOCK_DURATION)
            silence_blocks_need = int(self.SILENCE_DURATION / self.BLOCK_DURATION)

            recorded_blocks = []
            silence_run = 0
            speech_started = False

            with sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1,
                                dtype="int16", blocksize=block_size) as stream:
                for _ in range(max_blocks):
                    if not self._running:
                        break
                    block, _ = stream.read(block_size)
                    recorded_blocks.append(block.copy())
                    volume = np.abs(block).mean()
                    if volume > self.SILENCE_THRESHOLD:
                        speech_started = True
                        silence_run = 0
                    elif speech_started:
                        silence_run += 1
                        if silence_run >= silence_blocks_need:
                            break

            if not recorded_blocks or not speech_started:
                self.stopped.emit()
                return

            audio_np = np.concatenate(recorded_blocks, axis=0)
            audio_bytes = audio_np.tobytes()
            audio_data = sr.AudioData(audio_bytes, self.SAMPLE_RATE, 2)

            recognizer = sr.Recognizer()
            text = recognizer.recognize_google(audio_data)
            if text:
                self.recognized.emit(text)
            else:
                self.stopped.emit()

        except Exception as e:
            self.error.emit(str(e))
        finally:
            self._running = False
            self.stopped.emit()

    def stop(self):
        self._running = False
