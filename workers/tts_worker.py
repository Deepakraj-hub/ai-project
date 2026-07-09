"""
TTSWorker - queue-driven, interruptible edge-tts playback.
"""

import asyncio
import os
import queue
import tempfile
import threading
import time

from PySide6.QtCore import QThread, Signal


class TTSWorker(QThread):
    """Synthesizes and plays queued sentences while more text is generated."""

    started_speaking = Signal()
    finished_speaking = Signal()
    sentence_started = Signal(str)
    sentence_finished = Signal(str)
    error = Signal(str)

    def __init__(self, text=None, parent=None):
        super().__init__(parent)
        self._queue = queue.Queue()
        self._accepting = True
        self._finished_input = threading.Event()
        self._interrupt_event = threading.Event()
        self._has_started = False
        if text:
            self.add_text(text)
            self.finish()

    def add_text(self, text: str):
        text = (text or "").strip()
        if text and self._accepting and not self._interrupt_event.is_set():
            self._queue.put(text)

    def finish(self):
        self._accepting = False
        self._finished_input.set()

    def interrupt(self):
        self._accepting = False
        self._interrupt_event.set()
        self._finished_input.set()
        try:
            import sounddevice as sd
            sd.stop()
        except Exception:
            pass

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            import edge_tts
            from lily.voice import save_speech

            while not self._interrupt_event.is_set():
                if self._finished_input.is_set() and self._queue.empty():
                    break

                try:
                    text = self._queue.get(timeout=0.1)
                except queue.Empty:
                    continue

                if self._interrupt_event.is_set():
                    break

                filename = tempfile.mktemp(suffix=".mp3")
                try:
                    loop.run_until_complete(save_speech(edge_tts, text, filename))
                    if self._interrupt_event.is_set():
                        break

                    if not self._has_started:
                        self._has_started = True
                        self.started_speaking.emit()

                    self.sentence_started.emit(text)
                    try:
                        import sounddevice as sd
                        import soundfile as sf

                        data, samplerate = sf.read(filename, dtype="float32")
                        sd.play(data, samplerate)
                        duration = len(data) / float(samplerate)
                        deadline = time.monotonic() + duration
                        while time.monotonic() < deadline and not self._interrupt_event.is_set():
                            sd.sleep(25)
                        if self._interrupt_event.is_set():
                            sd.stop()
                        else:
                            sd.wait()
                    except ImportError:
                        pass
                    except Exception as playback_error:
                        self.error.emit(str(playback_error))
                    finally:
                        self.sentence_finished.emit(text)
                finally:
                    try:
                        os.remove(filename)
                    except Exception:
                        pass
        except Exception as e:
            if not self._interrupt_event.is_set():
                self.error.emit(str(e))
        finally:
            try:
                loop.close()
            except Exception:
                pass
            self.finished_speaking.emit()
