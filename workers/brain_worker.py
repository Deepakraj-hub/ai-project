"""
BrainWorker - QThread wrappers for Lily's background AI tasks.
"""

import re
import threading

from PySide6.QtCore import QThread, Signal


class BrainWorker(QThread):
    """Streams Gemma output and emits complete sentences as they arrive."""

    finished = Signal(str, dict)   # (ai_text, search_meta)
    token = Signal(str)
    sentence = Signal(str)
    interrupted = Signal()
    error = Signal(str)

    def __init__(self, memory, user_id, user_name, prompt,
                 location_engine, self_mod_engine, smart_search_engine,
                 force_search=False, auto_search=True, parent=None):
        super().__init__(parent)
        self._memory = memory
        self._user_id = user_id
        self._user_name = user_name
        self._prompt = prompt
        self._location_engine = location_engine
        self._self_mod_engine = self_mod_engine
        self._smart_search_engine = smart_search_engine
        self._force_search = force_search
        self._auto_search = auto_search
        self._interrupt_event = threading.Event()

    def interrupt(self):
        self._interrupt_event.set()

    def _pop_sentences(self, buffer):
        sentences = []
        pattern = re.compile(r'(.+?[.!?]["\')\]]?)(?:\s+|$)', re.DOTALL)
        while True:
            match = pattern.match(buffer)
            if not match:
                break
            sentence = re.sub(r"\s+", " ", match.group(1)).strip()
            if sentence:
                sentences.append(sentence)
            buffer = buffer[match.end():]
        return sentences, buffer

    def run(self):
        try:
            from jarvis import stream_brain

            full_text = []
            sentence_buffer = ""
            search_meta = {"used": False, "mode": None, "query": self._prompt, "sources": []}

            for event, payload in stream_brain(
                self._memory,
                self._user_id,
                self._user_name,
                self._prompt,
                self._location_engine,
                self._self_mod_engine,
                self._smart_search_engine,
                force_search=self._force_search,
                auto_search=self._auto_search,
                interrupt_event=self._interrupt_event,
            ):
                if self._interrupt_event.is_set():
                    self.interrupted.emit()
                    return

                if event == "meta":
                    search_meta = payload
                    continue

                if event == "chunk":
                    full_text.append(payload)
                    self.token.emit(payload)
                    sentence_buffer += payload
                    sentences, sentence_buffer = self._pop_sentences(sentence_buffer)
                    for sentence in sentences:
                        self.sentence.emit(sentence)
                    continue

                if event == "done":
                    final_text = payload
                    if sentence_buffer.strip():
                        self.sentence.emit(re.sub(r"\s+", " ", sentence_buffer).strip())
                    self.finished.emit(final_text, search_meta)
                    return

            if self._interrupt_event.is_set():
                self.interrupted.emit()
                return

            final_text = "".join(full_text).strip()
            if final_text:
                if sentence_buffer.strip():
                    self.sentence.emit(re.sub(r"\s+", " ", sentence_buffer).strip())
                self.finished.emit(final_text, search_meta)
        except Exception as e:
            if self._interrupt_event.is_set():
                self.interrupted.emit()
            else:
                self.error.emit(str(e))


class SmartSearchWorker(QThread):
    """Runs SmartSearchEngine.search() in the background."""

    finished = Signal(dict)   # search_payload
    error = Signal(str)

    def __init__(self, engine, query, force=True, parent=None):
        super().__init__(parent)
        self._engine = engine
        self._query = query
        self._force = force

    def run(self):
        try:
            payload = self._engine.search(self._query, force=self._force)
            self.finished.emit(payload)
        except Exception as e:
            self.error.emit(str(e))


class WarmUpWorker(QThread):
    """Pre-loads the Ollama model so the first chat is fast."""

    finished = Signal()

    def run(self):
        try:
            from jarvis import warm_up_brain
            warm_up_brain()
        except Exception:
            pass
        self.finished.emit()
