"""
BrainWorker — QThread wrapper for ask_brain() and smart search.
Runs AI inference off the main UI thread to keep the GUI responsive.
"""

from PySide6.QtCore import QThread, Signal


class BrainWorker(QThread):
    """Calls ask_brain() in a background thread and emits the result."""

    finished = Signal(str, dict)   # (ai_text, search_meta)
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

    def run(self):
        try:
            from jarvis import ask_brain
            ai_text, search_meta = ask_brain(
                self._memory,
                self._user_id,
                self._user_name,
                self._prompt,
                self._location_engine,
                self._self_mod_engine,
                self._smart_search_engine,
                force_search=self._force_search,
                auto_search=self._auto_search,
            )
            self.finished.emit(ai_text, search_meta)
        except Exception as e:
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
