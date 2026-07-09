"""
LilyWindow — Full-screen avatar with real-time duplex voice.
No chat interface. Voice only. Avatar fills the screen.
Moshi handles continuous listening, Gemma4 handles reasoning.
"""

import re
import os
import sys
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QFrame, QSizePolicy, QPushButton, QGraphicsDropShadowEffect,
    QApplication, QLineEdit
)

from widgets.audio_visualizer import AudioVisualizerBars
from workers.brain_worker import BrainWorker, WarmUpWorker
from workers.tts_worker import TTSWorker
from workers.moshi_worker import MoshiVoiceWorker


# ── Expression detection ───────────────────────────────────────────────────
def detect_expression(text: str) -> str:
    if not text:
        return "neutral"
    t = text.lower()
    happy_words = [
        "smile", "😊", "happy", "joy", "spirit", "kaapi", "great", "awesome",
        "wonderful", "excellent", "amazing", "fantastic", "glad", "delighted",
        "cheerful", "bright", "sunshine", "laugh", "fun", "enjoy", "love",
        "beautiful", "perfect", "brilliant", "congratulations", "celebrate"
    ]
    sad_words = [
        "sad", "sorry", "error", "fail", "intercepted", "unfortunately",
        "regret", "apologize", "disappointed", "heartbroken",
        "grief", "loss", "pain", "hurt", "cry", "tears", "depressed",
    ]
    angry_words = [
        "angry", "frustrated", "wrong", "stop", "hate", "😡", "mad", "furious",
        "irritated", "annoyed", "outrage", "rage",
    ]
    shy_words = [
        "shy", "blush", "maybe", "perhaps", "😳", "🙈", "embarrassed",
        "nervous", "awkward",
    ]
    if any(w in t for w in happy_words):
        return "smiling"
    if any(w in t for w in sad_words):
        return "sad"
    if any(w in t for w in angry_words):
        return "angry"
    if any(w in t for w in shy_words):
        return "shy"
    return "neutral"


def is_agent_task(text: str) -> bool:
    lower = text.lower().strip()
    if lower.startswith(("agent ", "task ")):
        return True
    agent_verbs = (
        "build", "create", "make", "develop", "design", "generate", "automate",
        "implement", "fix", "refactor", "test", "run", "analyze", "review",
        "summarize", "organize", "open", "convert", "write", "type", "click",
        "launch", "go", "visit", "take", "capture", "look", "see",
    )
    agent_objects = (
        "website", "web app", "web page", "landing page", "project", "app",
        "script", "file", "folder", "site", "automation", "notepad",
        "calculator", "desktop", "window", "browser", "youtube", "google",
        "screen", "screenshot",
    )
    if any(phrase in lower for phrase in (
        "see my screen", "look at my screen", "what is on my screen",
        "analyze my screen", "take a screenshot", "capture my screen",
        "go to youtube", "open youtube", "visit youtube",
    )):
        return True
    if any(lower.startswith(v + " ") for v in agent_verbs) and any(obj in lower for obj in agent_objects):
        return True
    return False


def normalize_agent_goal(text: str) -> str:
    lower = text.lower().strip()
    for prefix in ("agent ", "task "):
        if lower.startswith(prefix):
            return text.strip()[len(prefix):].strip()
    return text.strip()


class SpeechBubbleWidget(QWidget):
    """Premium floating speech bubble positioned near the center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setVisible(False)
        self.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel("")
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._label.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(30, 25, 50, 240), stop:1 rgba(20, 15, 35, 240));
            color: #f1f5f9;
            border: 1.5px solid rgba(168, 85, 247, 0.7);
            border-radius: 18px;
            padding: 16px 18px;
            font-size: 14px;
            font-weight: 500;
        """)
        layout.addWidget(self._label)

        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self.hide)
        self._hide_timer.setSingleShot(True)

    def show_text(self, speaker: str, text: str):
        if not text or not text.strip():
            return
        prefix = "You" if speaker == "user" else "Lily"
        self._label.setText(f"{prefix}: {text.strip()}")
        self.setVisible(True)
        display_time = max(3200, min(9000, len(text) * 70))
        self._hide_timer.start(display_time)


class ChatInputOverlay(QWidget):
    """Premium floating chat input at the bottom."""

    def __init__(self, parent=None, submit_callback=None):
        super().__init__(parent)
        self._submit_callback = submit_callback
        self.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(12)

        self._input = QLineEdit(self)
        self._input.setPlaceholderText("Speak to Lily or type here...")
        self._input.setMinimumHeight(50)
        self._input.setStyleSheet("""
            QLineEdit {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(30, 25, 50, 220), stop:1 rgba(20, 15, 40, 220));
                color: #f1f5f9;
                border: 1px solid rgba(168, 85, 247, 0.4);
                border-radius: 12px;
                padding: 0 16px;
                font-size: 15px;
                font-weight: 500;
            }
            QLineEdit:focus {
                border: 2px solid rgba(168, 85, 247, 0.8);
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(35, 30, 60, 240), stop:1 rgba(25, 20, 45, 240));
            }
        """)
        self._input.returnPressed.connect(self._submit)
        layout.addWidget(self._input)

        self._send_button = QPushButton("Send", self)
        self._send_button.setMinimumHeight(50)
        self._send_button.setMinimumWidth(80)
        self._send_button.setCursor(Qt.PointingHandCursor)
        self._send_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a855f7, stop:1 #7c3aed);
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: 700;
                font-size: 14px;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #c084fc, stop:1 #a855f7);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #9333ea, stop:1 #7c3aed);
            }
        """)
        self._send_button.clicked.connect(self._submit)
        layout.addWidget(self._send_button)

    def _submit(self):
        text = self._input.text().strip()
        if not text:
            return
        if self._submit_callback:
            self._submit_callback(text)
        self._input.clear()
        self._input.setFocus()

    def focus_input(self):
        self._input.setFocus()


class StatusOverlay(QWidget):
    """Premium floating status bar overlay at the top."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setFixedHeight(70)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 12, 32, 12)
        layout.setSpacing(0)

        # Status indicator (left)
        self._status = QLabel("● INITIALIZING")
        self._status.setStyleSheet("""
            font-size: 11px; font-weight: 700; letter-spacing: 3px;
            color: #4ade80; background: transparent;
        """)
        layout.addWidget(self._status)

        layout.addStretch()

        # Brand (center)
        brand = QLabel("LILY")
        brand.setStyleSheet("""
            font-size: 28px; font-weight: 900; letter-spacing: 12px;
            color: #e0e7ff; background: transparent;
            text-shadow: 0 0 30px rgba(192, 132, 252, 0.5);
        """)
        brand.setAlignment(Qt.AlignCenter)
        layout.addWidget(brand)

        layout.addStretch()

        # Expression tag (right)
        self._expression = QLabel("○ IDLE")
        self._expression.setStyleSheet("""
            font-size: 11px; font-weight: 600; letter-spacing: 2px;
            color: #94a3b8; background: transparent;
        """)
        layout.addWidget(self._expression)

    def set_status(self, text: str):
        self._status.setText(text)
        if "ACTIVE" in text or "LISTENING" in text:
            self._status.setStyleSheet("""
                font-size: 11px; font-weight: 700; letter-spacing: 3px;
                color: #4ade80; background: transparent;
            """)
        elif "SPEAKING" in text:
            self._status.setStyleSheet("""
                font-size: 11px; font-weight: 700; letter-spacing: 3px;
                color: #c084fc; background: transparent;
            """)
        elif "PROCESSING" in text:
            self._status.setStyleSheet("""
                font-size: 11px; font-weight: 700; letter-spacing: 3px;
                color: #22d3ee; background: transparent;
            """)
        elif "ERROR" in text:
            self._status.setStyleSheet("""
                font-size: 11px; font-weight: 700; letter-spacing: 3px;
                color: #ef4444; background: transparent;
            """)
        else:
            self._status.setStyleSheet("""
                font-size: 11px; font-weight: 700; letter-spacing: 3px;
                color: #94a3b8; background: transparent;
            """)

    def set_expression(self, text: str):
        self._expression.setText(text)

    def paintEvent(self, event):
        """Draw a premium gradient background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(10, 14, 32, 240))
        grad.setColorAt(1, QColor(10, 14, 32, 160))
        painter.fillRect(self.rect(), grad)
        # Bottom border
        painter.setPen(QColor(99, 102, 241, 80))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)
        painter.end()



class BottomOverlay(QWidget):
    """Premium floating transcript bar at the bottom."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 12, 40, 20)

        self._transcript = QLabel("")
        self._transcript.setAlignment(Qt.AlignCenter)
        self._transcript.setWordWrap(True)
        self._transcript.setStyleSheet("""
            font-size: 15px; font-weight: 500; color: rgba(241, 245, 249, 200);
            background: transparent;
        """)
        layout.addWidget(self._transcript)

        # Auto-hide timer
        self._hide_timer = QTimer(self)
        self._hide_timer.timeout.connect(self._fade_text)
        self._hide_timer.setSingleShot(True)

    def show_text(self, speaker: str, text: str):
        prefix = "🎤 You" if speaker == "user" else "💜 Lily"
        self._transcript.setText(f"{prefix}: {text}")
        self._transcript.setStyleSheet(f"""
            font-size: 15px; font-weight: 500;
            color: {'rgba(241, 245, 249, 200)' if speaker == 'user' else 'rgba(192, 132, 252, 220)'};
            background: transparent;
        """)
        # Display time scales with text length
        display_time = max(6000, min(20000, len(text) * 100))
        self._hide_timer.start(display_time)

    def _fade_text(self):
        self._transcript.setText("")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor(10, 14, 32, 0))
        grad.setColorAt(0.7, QColor(10, 14, 32, 180))
        grad.setColorAt(1, QColor(10, 14, 32, 240))
        painter.fillRect(self.rect(), grad)
        painter.end()



class LilyWindow(QMainWindow):
    """Main LILY AI window — full-screen avatar with real-time duplex voice."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LILY — Cognitive AI Core v2.0")
        self.setMinimumSize(1000, 700)
        self.resize(1400, 900)
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0e20, stop:0.5 #1a1530, stop:1 #0f0d19);
            }
        """)

        # ── Initialize AI engines ──
        from jarvis import Memory, LocationEngine, SelfModEngine, SmartSearchEngine
        self._memory = Memory()
        self._location_engine = LocationEngine(self._memory)
        self._self_mod_engine = SelfModEngine(self._memory)
        self._smart_search_engine = SmartSearchEngine()
        self._user_id = 1
        self._user_name = "Deepak"

        # State
        self._brain_worker = None
        self._tts_worker = None
        self._moshi_worker = None
        self._moshi_server_process = None
        self._is_speaking = False
        self._assistant_stream_text = ""

        # ── Build UI ──
        self._build_ui()
        self._load_theme()
        self._status_overlay.set_status("● INITIALIZING")
        self._status_overlay.set_expression("● READY")
        self._bottom_overlay.show_text("assistant", "Lily is waking up and preparing the experience.")

        # ── Warm up brain model in background ──
        self._warmup = WarmUpWorker(self)
        self._warmup.start()

        # ── Detect location in background ──
        threading.Thread(
            target=lambda: self._location_engine.detect(self._user_id),
            daemon=True
        ).start()
        
        # ── Launch Moshi Server ──
        self._launch_moshi_server()

        # ── Auto-start duplex voice after a brief delay (let avatar load) ──
        QTimer.singleShot(2500, self._start_duplex)

    def _launch_moshi_server(self):
        """Silently attempt to launch the Moshi server in the background."""
        import subprocess
        self._status_overlay.set_status("● STARTING MOSHI SERVER")
        try:
            creationflags = 0
            if sys.platform == "win32":
                creationflags = subprocess.CREATE_NO_WINDOW

            self._moshi_server_process = subprocess.Popen(
                [sys.executable, "-m", "moshi.server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
            print("[LILY] Moshi server background process started.")
        except Exception as e:
            print(f"[LILY] Failed to start Moshi server: {e}")

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        # Single full-screen layout — avatar fills everything
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═══ VISUALIZER (center) ═══
        self._visualizer = AudioVisualizerBars(central)
        self._visualizer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self._visualizer)

        # ═══ OVERLAY: Status bar (top) ═══
        self._status_overlay = StatusOverlay(central)
        self._status_overlay.raise_()

        # ═══ OVERLAY: Transcript bar (bottom) ═══
        self._bottom_overlay = BottomOverlay(central)
        self._bottom_overlay.raise_()

        # ═══ OVERLAY: Chat input bar (bottom) ═══
        self._chat_input = ChatInputOverlay(central, submit_callback=self._submit_chat_text)
        self._chat_input.raise_()

        # ═══ OVERLAY: Speech bubble ═══
        self._speech_bubble = SpeechBubbleWidget(central)
        self._speech_bubble.raise_()

    def resizeEvent(self, event):
        """Keep overlays pinned to top/bottom of window."""
        super().resizeEvent(event)
        w = self.centralWidget().width()
        h = self.centralWidget().height()
        self._status_overlay.setGeometry(0, 0, w, 70)
        self._bottom_overlay.setGeometry(0, h - 110, w, 110)
        self._chat_input.setGeometry(max(32, w // 10), h - 180, max(350, w - (w // 5)), 60)
        self._speech_bubble.setGeometry(max(32, w // 5), h // 3, min(500, max(300, w - (w // 3))), 120)

    def _load_theme(self):
        theme_path = os.path.join(os.path.dirname(__file__), "styles", "theme.qss")
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(self.styleSheet() + "\n" + f.read())
        except FileNotFoundError:
            print(f"[LILY] Theme file not found: {theme_path}")

    # ── Duplex Voice ─────────────────────────────────────────────────────

    def _start_duplex(self):
        """Start the continuous duplex voice listener."""
        try:
            self._moshi_worker = MoshiVoiceWorker(parent=self)
            self._moshi_worker.status_changed.connect(self._on_moshi_status)
            self._moshi_worker.user_speech.connect(self._on_user_speech)
            self._moshi_worker.interrupt_requested.connect(self._interrupt_current_response)
            self._moshi_worker.error.connect(self._on_moshi_error)
            self._moshi_worker.start()
        except Exception as exc:
            self._status_overlay.set_status("● READY")
            self._status_overlay.set_expression("● READY")
            self._bottom_overlay.show_text("assistant", f"Voice mode is available, but startup hit a snag: {exc}")

    def _on_moshi_status(self, status: str):
        self._status_overlay.set_status(status)
        if "LISTENING" in status:
            self._status_overlay.set_expression("● LISTENING")
        elif "PROCESSING" in status:
            self._status_overlay.set_expression("● THINKING")

    def _on_moshi_error(self, error_msg: str):
        print(f"[Moshi Error] {error_msg}")
        self._status_overlay.set_status("● ERROR")
        # Try to restart after a delay
        QTimer.singleShot(3000, self._start_duplex)

    def _submit_chat_text(self, text: str):
        """Handle typed chat input and send it to Lily."""
        self._on_user_speech(text)

    def _on_user_speech(self, text: str):
        """User said something — route to Gemma4 brain."""
        text = (text or "").strip()
        if not text:
            return

        self._interrupt_current_response()
        print(f"[User] {text}")
        self._bottom_overlay.show_text("user", text)
        self._speech_bubble.show_text("user", text)
        self._status_overlay.set_expression("● THINKING")

        # Check if it's an agent task
        if is_agent_task(text):
            self._start_agent_task(normalize_agent_goal(text))
            return

        # Route to Gemma4 brain
        self._brain_worker = BrainWorker(
            self._memory, self._user_id, self._user_name, text,
            self._location_engine, self._self_mod_engine,
            self._smart_search_engine,
            force_search=False,
            auto_search=True,
            parent=self,
        )
        self._assistant_stream_text = ""
        self._brain_worker.sentence.connect(self._on_brain_sentence)
        self._brain_worker.finished.connect(self._on_brain_response)
        self._brain_worker.interrupted.connect(self._on_brain_interrupted)
        self._brain_worker.error.connect(self._on_brain_error)
        self._brain_worker.start()

    def _on_brain_sentence(self, sentence: str):
        """Queue the next generated sentence for immediate speech."""
        sender = self.sender()
        if sender is not self._brain_worker:
            return
        sentence = (sentence or "").strip()
        if not sentence:
            return

        self._assistant_stream_text = (
            f"{self._assistant_stream_text} {sentence}".strip()
        )
        self._bottom_overlay.show_text("assistant", self._assistant_stream_text)
        self._speech_bubble.show_text("assistant", self._assistant_stream_text)

        if not self._tts_worker or not self._tts_worker.isRunning():
            self._start_streaming_tts()
        self._tts_worker.add_text(sentence)

    def _on_brain_response(self, ai_text: str, search_meta: dict):
        """Gemma4 responded — speak it immediately."""
        sender = self.sender()
        if sender is not self._brain_worker:
            return
        print(f"[Lily] {ai_text}")

        # Expression
        expr = detect_expression(ai_text)
        self._visualizer.set_expression(expr)

        # Show transcript and speech bubble
        self._bottom_overlay.show_text("assistant", ai_text)
        self._speech_bubble.show_text("assistant", ai_text)

        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.finish()
        self._brain_worker = None

    def _on_brain_interrupted(self):
        sender = self.sender()
        if sender is self._brain_worker:
            self._brain_worker = None

    def _on_brain_error(self, error_msg: str):
        """Brain error — tell user and resume listening."""
        print(f"[Brain Error] {error_msg}")
        self._avatar.set_expression("sad")
        self._speak("Sorry, I had a processing error. Try again.")

    # ── Agent Tasks ──────────────────────────────────────────────────────

    def _start_agent_task(self, goal: str):
        from workers.agent_worker import AgentSessionWorker

        self._status_overlay.set_expression("● AGENT ACTIVE")
        self._speak(f"Agent mode engaged. Working on: {goal}")
        self._agent_worker = AgentSessionWorker(goal, parent=self)
        self._agent_worker.step_progress.connect(self._on_agent_step)
        self._agent_worker.finished_result.connect(self._on_agent_finished)
        self._agent_worker.error.connect(self._on_agent_error)
        self._agent_worker.start()

    def _on_agent_step(self, message: str):
        self._bottom_overlay.show_text("assistant", f"⚙ {message}")

    def _on_agent_finished(self, payload: dict):
        status = payload.get("status", "failed")
        message = payload.get("message", "Task finished.")
        preview_url = payload.get("preview_url")

        if preview_url:
            import webbrowser
            webbrowser.open(preview_url, new=2)
            self._speak("I finished your task and opened the preview.")
        elif status == "completed":
            self._speak("Your agent task is complete.")
        else:
            self._speak("The agent task did not fully complete.")

    def _on_agent_error(self, error_msg: str):
        self._speak(f"Agent error: {error_msg}")

    # ── TTS (with echo cancellation) ─────────────────────────────────────

    def _start_streaming_tts(self):
        self._is_speaking = True
        self._visualizer.set_talking(True)
        self._status_overlay.set_status("● SPEAKING")
        self._status_overlay.set_expression("● SPEAKING")
        if self._moshi_worker:
            self._moshi_worker.set_lily_speaking(True)

        self._tts_worker = TTSWorker(parent=self)
        self._tts_worker.started_speaking.connect(self._on_tts_started)
        self._tts_worker.finished_speaking.connect(self._on_tts_finished)
        self._tts_worker.error.connect(lambda e: print(f"[TTS Error] {e}"))
        self._tts_worker.start()

    def _speak(self, text: str):
        """Speak text. Mic is paused BEFORE this and resumed AFTER."""
        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.interrupt()
        self._is_speaking = True
        self._visualizer.set_talking(True)
        self._status_overlay.set_status("● SPEAKING")
        self._status_overlay.set_expression("● SPEAKING")
        self._bottom_overlay.show_text("assistant", text)

        if self._moshi_worker:
            self._moshi_worker.set_lily_speaking(True)

        self._tts_worker = TTSWorker(text, parent=self)
        self._tts_worker.started_speaking.connect(self._on_tts_started)
        self._tts_worker.finished_speaking.connect(self._on_tts_finished)
        self._tts_worker.error.connect(lambda e: print(f"[TTS Error] {e}"))
        self._tts_worker.start()

    def _on_tts_started(self):
        """TTS audio playback has begun."""
        self._visualizer.set_talking(True)

    def _on_tts_finished(self):
        sender = self.sender()
        if sender is not self._tts_worker:
            return
        """TTS finished — resume mic listening."""
        self._is_speaking = False
        self._visualizer.set_talking(False)
        self._status_overlay.set_status("● DUPLEX ACTIVE")
        self._status_overlay.set_expression("● LISTENING")
        self._bottom_overlay._fade_text()

        if self._moshi_worker:
            self._moshi_worker.set_lily_speaking(False)
        self._tts_worker = None

    # ── Cleanup ──────────────────────────────────────────────────────────

    def _interrupt_current_response(self):
        interrupted = False
        if self._brain_worker and self._brain_worker.isRunning():
            self._brain_worker.interrupt()
            interrupted = True
        if self._tts_worker and self._tts_worker.isRunning():
            self._tts_worker.interrupt()
            self._tts_worker = None
            interrupted = True
        if interrupted:
            self._visualizer.set_talking(False)
            self._status_overlay.set_status("● INTERRUPTED")
            self._status_overlay.set_expression("● THINKING")
            if self._moshi_worker:
                self._moshi_worker.set_lily_speaking(False)

    def closeEvent(self, event):
        self._interrupt_current_response()
        if self._moshi_worker:
            self._moshi_worker.stop()
        if self._moshi_server_process:
            try:
                self._moshi_server_process.terminate()
            except Exception:
                pass
        super().closeEvent(event)
