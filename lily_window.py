"""
LilyWindow — Main application window.
Assembles the avatar panel (left) and console panel (right),
and wires up all signal/slot connections to the AI brain.
"""

import re
import os
import sys
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QLinearGradient, QFont
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QFrame, QSizePolicy, QSplitter, QApplication
)

from widgets.avatar_widget import AvatarWidget
from widgets.chat_widget import ChatWidget
from widgets.toolbar_widget import ToolbarWidget
from widgets.input_widget import InputWidget
from widgets.info_panels import TopicsPanel, RecallsPanel, SearchBanner
from workers.brain_worker import BrainWorker, WarmUpWorker
from workers.tts_worker import TTSWorker, VoiceInputWorker


# ── Expression detection (ported from app.py) ──────────────────────────────
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


# ── Topic / Recall extraction (ported from app.py) ─────────────────────────
def extract_topics(text: str) -> list:
    topics = []
    text_lower = text.lower()
    patterns = [
        r"topic\s+is\s+([\w\s]+?)[,.]",
        r"discuss(?:ing)?\s+([\w\s]+?)[,.]",
        r"about\s+([\w\s]+?)[,.]",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text_lower):
            topic = match.strip()
            if 3 < len(topic) < 50:
                topics.append(topic)
    words = re.findall(r'\b[A-Z][a-z]+\b', text)
    counts = {}
    for w in words:
        counts[w] = counts.get(w, 0) + 1
    for w, c in counts.items():
        if c >= 2 and len(w) > 3 and w.lower() not in topics:
            topics.append(w.lower())
    return topics[:5]


def extract_recalls(text: str) -> list:
    recalls = []
    patterns = [
        r"remember\s+([\w\s]+?)[,.]",
        r"recall\s+([\w\s]+?)[,.]",
        r"you mentioned\s+([\w\s]+?)[,.]",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, text.lower()):
            recall = match.strip()
            if 5 < len(recall) < 80:
                recalls.append(recall)
    return recalls[:3]


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
    if "interactive" in lower and any(obj in lower for obj in ("website", "web app", "site", "ui")):
        return True
    return False


def normalize_agent_goal(text: str) -> str:
    lower = text.lower().strip()
    for prefix in ("agent ", "task "):
        if lower.startswith(prefix):
            return text.strip()[len(prefix):].strip()
    return text.strip()


class GradientStripe(QWidget):
    """Animated gradient stripe at the top of the console panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("gradientStripe")
        self.setFixedHeight(2)
        self._offset = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self):
        self._offset += 0.02
        if self._offset > 2.0:
            self._offset -= 2.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        o = self._offset
        grad.setColorAt(max(0, min(1, 0.0 + o * 0.5 % 1)), QColor(168, 85, 247))
        grad.setColorAt(max(0, min(1, 0.5 + o * 0.5 % 1)), QColor(34, 211, 238))
        grad.setColorAt(1.0, QColor(168, 85, 247))
        painter.fillRect(self.rect(), grad)
        painter.end()


class LilyWindow(QMainWindow):
    """Main LILY AI desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("LILY — Cognitive AI Core v2.0")
        self.setMinimumSize(1100, 700)
        self.resize(1300, 800)

        # Dark background for the window itself
        self.setStyleSheet("QMainWindow { background: #060610; }")

        # ── Initialize AI engines ──
        from jarvis import Memory, LocationEngine, SelfModEngine, SmartSearchEngine
        self._memory = Memory()
        self._location_engine = LocationEngine(self._memory)
        self._self_mod_engine = SelfModEngine(self._memory)
        self._smart_search_engine = SmartSearchEngine()
        self._user_id = 1
        self._user_name = "Deepak"

        # State
        self._topics = []
        self._recalls = []
        self._is_memory_connected = True
        self._brain_worker = None
        self._tts_worker = None
        self._voice_worker = None
        self._is_listening = False

        # ── Build UI ──
        self._build_ui()
        self._load_theme()

        # ── Warm up brain model in background ──
        self._warmup = WarmUpWorker(self)
        self._warmup.start()

        # ── Detect location in background ──
        threading.Thread(
            target=lambda: self._location_engine.detect(self._user_id),
            daemon=True
        ).start()

        # ── Clock timer ──
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)

        # Initial message
        self._chat.add_message(
            "assistant",
            "System online. LILY Core initialised. Memory core connected.\n"
            "Agent mode: give me a task like \"build an interactive website about trees and planets\" "
            "and I'll plan, ask permission when needed, then show you the result."
        )

        self._agent_worker = None

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═══ LEFT: Avatar Panel ═══
        avatar_panel = QWidget()
        avatar_panel.setObjectName("avatarPanel")
        avatar_layout = QVBoxLayout(avatar_panel)
        avatar_layout.setContentsMargins(0, 0, 0, 0)
        avatar_layout.setSpacing(0)

        # Brand header
        brand_container = QWidget()
        brand_layout = QVBoxLayout(brand_container)
        brand_layout.setContentsMargins(0, 24, 0, 0)
        brand_layout.setAlignment(Qt.AlignCenter)

        self._brand_title = QLabel("LILY")
        self._brand_title.setObjectName("brandTitle")
        self._brand_title.setAlignment(Qt.AlignCenter)
        brand_layout.addWidget(self._brand_title)

        self._brand_sub = QLabel("COGNITIVE AI CORE v2.0")
        self._brand_sub.setObjectName("brandSub")
        self._brand_sub.setAlignment(Qt.AlignCenter)
        brand_layout.addWidget(self._brand_sub)

        avatar_layout.addWidget(brand_container)

        # Avatar
        self._avatar = AvatarWidget()
        self._avatar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        avatar_layout.addWidget(self._avatar)

        # Status bar
        status_bar = QWidget()
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(24, 0, 24, 20)

        self._status_label = QLabel("● CORE ONLINE")
        self._status_label.setObjectName("statusLabel")
        status_layout.addWidget(self._status_label)

        status_layout.addStretch()

        self._expression_tag = QLabel("○ IDLE")
        self._expression_tag.setObjectName("expressionTag")
        status_layout.addWidget(self._expression_tag)

        avatar_layout.addWidget(status_bar)

        main_layout.addWidget(avatar_panel, stretch=6)

        # ═══ RIGHT: Console Panel ═══
        console_panel = QWidget()
        console_panel.setObjectName("consolePanel")
        console_layout = QVBoxLayout(console_panel)
        console_layout.setContentsMargins(20, 0, 20, 20)
        console_layout.setSpacing(0)

        # Gradient stripe
        self._gradient_stripe = GradientStripe()
        console_layout.addWidget(self._gradient_stripe)
        console_layout.addSpacing(18)

        # Panel header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self._panel_title = QLabel("CONSOLE")
        self._panel_title.setObjectName("panelTitle")
        header_layout.addWidget(self._panel_title)

        header_layout.addStretch()

        self._panel_time = QLabel()
        self._panel_time.setObjectName("panelTime")
        header_layout.addWidget(self._panel_time)

        console_layout.addWidget(header)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background: rgba(148, 163, 184, 20); max-height: 1px;")
        console_layout.addWidget(sep)
        console_layout.addSpacing(12)

        # Toolbar
        self._toolbar = ToolbarWidget()
        self._toolbar.memory_toggled.connect(self._on_memory_toggled)
        self._toolbar.topics_toggled.connect(self._on_topics_toggled)
        self._toolbar.recalls_toggled.connect(self._on_recalls_toggled)
        self._toolbar.search_clicked.connect(self._on_search)
        console_layout.addWidget(self._toolbar)
        console_layout.addSpacing(10)

        # Search banner
        self._search_banner = SearchBanner()
        console_layout.addWidget(self._search_banner)

        # Topics panel
        self._topics_panel = TopicsPanel()
        console_layout.addWidget(self._topics_panel)

        # Recalls panel
        self._recalls_panel = RecallsPanel()
        console_layout.addWidget(self._recalls_panel)

        # Chat area
        self._chat = ChatWidget()
        self._chat.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        console_layout.addWidget(self._chat)
        console_layout.addSpacing(12)

        # Input area
        self._input = InputWidget()
        self._input.message_sent.connect(self._on_send_message)
        self._input.voice_toggled.connect(self._on_voice_toggle)
        console_layout.addWidget(self._input)

        main_layout.addWidget(console_panel, stretch=4)

    def _load_theme(self):
        theme_path = os.path.join(os.path.dirname(__file__), "styles", "theme.qss")
        try:
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(self.styleSheet() + "\n" + f.read())
        except FileNotFoundError:
            print(f"[LILY] Theme file not found: {theme_path}")

    def _update_clock(self):
        from datetime import datetime
        self._panel_time.setText(datetime.now().strftime("%H:%M:%S"))

    # ── Message handling ─────────────────────────────────────────────────

    def _on_send_message(self, text: str, force_search: bool = False):
        """Handle user sending a message."""
        self._chat.add_message("user", text)
        self._chat.show_thinking()
        self._input.set_enabled(False)

        if is_agent_task(text):
            self._start_agent_task(normalize_agent_goal(text))
            return

        self._brain_worker = BrainWorker(
            self._memory, self._user_id, self._user_name, text,
            self._location_engine, self._self_mod_engine,
            self._smart_search_engine,
            force_search=force_search,
            auto_search=True,
            parent=self,
        )
        self._brain_worker.finished.connect(self._on_brain_response)
        self._brain_worker.error.connect(self._on_brain_error)
        self._brain_worker.start()

    def _start_agent_task(self, goal: str):
        from workers.agent_worker import AgentSessionWorker

        self._expression_tag.setText("● AGENT ACTIVE")
        self._chat.add_message("assistant", f"Agent mode engaged.\nGoal: {goal}\nPlanning steps...")
        self._agent_worker = AgentSessionWorker(goal, parent=self)
        self._agent_worker.permission_required.connect(self._on_agent_permission_required)
        self._agent_worker.step_progress.connect(self._on_agent_step_progress)
        self._agent_worker.finished_result.connect(self._on_agent_finished)
        self._agent_worker.error.connect(self._on_agent_error)
        self._agent_worker.start()

    def _on_agent_permission_required(self, payload: dict):
        from lily.brain.permissions import PermissionDecision
        from widgets.permission_dialog import PermissionDialog

        dialog = PermissionDialog(payload, self)
        approved = dialog.exec() == PermissionDialog.Accepted
        decision = PermissionDecision(
            approved=approved,
            always_allow=dialog.always_allow if approved else False,
            reason="Approved in desktop UI" if approved else "Denied by user",
        )
        if self._agent_worker:
            self._agent_worker.supply_permission(decision)
        if not approved:
            self._chat.add_message("assistant", "Permission denied. Lily stopped that action.")

    def _on_agent_step_progress(self, message: str):
        self._chat.add_message("assistant", f"⚙ {message}")

    def _on_agent_finished(self, payload: dict):
        self._chat.hide_thinking()
        self._input.set_enabled(True)
        self._input.focus_input()

        status = payload.get("status", "failed")
        message = payload.get("message", "Task finished.")
        observations = payload.get("observations") or []
        preview_url = payload.get("preview_url")
        artifacts = payload.get("artifacts") or []

        lines = [f"Agent task {status}.", "", message]
        if observations:
            lines.append("")
            lines.append("Steps:")
            for obs in observations[-6:]:
                mark = "✓" if obs.get("success") else "✗"
                lines.append(f"{mark} {obs.get('summary', 'Step')}")
                analysis = (obs.get("data") or {}).get("analysis")
                if analysis:
                    lines.append(f"Screen analysis: {analysis}")
        if artifacts:
            lines.append("")
            lines.append("Artifacts:")
            for path in artifacts[:5]:
                lines.append(f"• {path}")

        self._chat.add_message("assistant", "\n".join(lines))
        self._avatar.set_expression("smiling" if status == "completed" else "sad")
        self._update_expression_tag(self._avatar._expression, speaking=False)

        browser_already_opened = any(
            "Opened browser" in (obs.get("summary") or "")
            for obs in observations
        )

        if preview_url and not browser_already_opened:
            import webbrowser
            webbrowser.open(preview_url, new=2)
            self._chat.add_message("assistant", f"Opened preview in your browser:\n{preview_url}")
            self._speak("I finished your task and opened the preview.")
        elif preview_url:
            self._chat.add_message("assistant", f"Preview opened in your browser:\n{preview_url}")
            self._speak("I finished your task and opened the preview.")
        elif status == "completed":
            self._speak("Your agent task is complete.")
        else:
            self._speak("The agent task did not fully complete.")

    def _on_agent_error(self, error_msg: str):
        self._chat.hide_thinking()
        self._input.set_enabled(True)
        self._chat.add_message("assistant", f"Agent error: {error_msg}")
        self._avatar.set_expression("sad")
        self._update_expression_tag("sad", speaking=False)

    def _on_agent_response(self, message: str):
        self._on_agent_finished({"status": "completed", "message": message, "observations": []})

    def _on_brain_response(self, ai_text: str, search_meta: dict):
        """Handle AI response from brain worker."""
        self._chat.hide_thinking()
        self._chat.add_message("assistant", ai_text)
        self._input.set_enabled(True)
        self._input.focus_input()

        # Expression
        expr = detect_expression(ai_text)
        self._avatar.set_expression(expr)
        self._update_expression_tag(expr, speaking=True)

        # Search results
        if search_meta.get("used"):
            self._search_banner.show_results(
                search_meta.get("query", ""),
                search_meta.get("mode", "web"),
                search_meta.get("sources", [])
            )
        else:
            self._search_banner.hide_results()

        # Topics / Recalls
        new_topics = extract_topics(ai_text)
        new_recalls = extract_recalls(ai_text)
        for t in new_topics:
            if t not in self._topics:
                self._topics.append(t)
        for r in new_recalls:
            if r not in self._recalls:
                self._recalls.append(r)

        self._toolbar.update_topic_count(len(self._topics))
        self._toolbar.update_recall_count(len(self._recalls))
        self._topics_panel.update_topics(self._topics)
        self._recalls_panel.update_recalls(self._recalls)

        # TTS
        self._speak(ai_text)

    def _on_brain_error(self, error_msg: str):
        """Handle brain worker error."""
        self._chat.hide_thinking()
        self._chat.add_message(
            "assistant",
            f"LILY: Memory core error. Details: {error_msg}"
        )
        self._input.set_enabled(True)
        self._avatar.set_expression("sad")
        self._update_expression_tag("sad", speaking=False)

    # ── TTS ───────────────────────────────────────────────────────────────

    def _speak(self, text: str):
        """Speak text via edge-tts in background."""
        self._avatar.set_talking(True)
        self._update_expression_tag(self._avatar._expression, speaking=True)

        self._tts_worker = TTSWorker(text, parent=self)
        self._tts_worker.finished_speaking.connect(self._on_speech_done)
        self._tts_worker.error.connect(lambda e: print(f"[TTS Error] {e}"))
        self._tts_worker.start()

    def _on_speech_done(self):
        self._avatar.set_talking(False)
        self._avatar.set_expression("neutral")
        self._update_expression_tag("neutral", speaking=False)

    # ── Voice input ──────────────────────────────────────────────────────

    def _on_voice_toggle(self):
        if self._is_listening:
            self._stop_listening()
        else:
            self._start_listening()

    def _start_listening(self):
        self._is_listening = True
        self._input.set_listening(True)

        self._voice_worker = VoiceInputWorker(parent=self)
        self._voice_worker.recognized.connect(self._on_voice_recognized)
        self._voice_worker.stopped.connect(self._on_voice_stopped)
        self._voice_worker.error.connect(self._on_voice_error)
        self._voice_worker.start()

    def _stop_listening(self):
        if self._voice_worker:
            self._voice_worker.stop()
        self._is_listening = False
        self._input.set_listening(False)

    def _on_voice_recognized(self, text: str):
        self._is_listening = False
        self._input.set_listening(False)
        self._input.set_text(text)
        self._on_send_message(text)

    def _on_voice_stopped(self):
        self._is_listening = False
        self._input.set_listening(False)

    def _on_voice_error(self, error_msg: str):
        self._is_listening = False
        self._input.set_listening(False)
        print(f"[Voice Error] {error_msg}")

    # ── Toolbar actions ──────────────────────────────────────────────────

    def _on_memory_toggled(self, connected: bool):
        self._is_memory_connected = connected
        if connected:
            self._status_label.setText("● CORE ONLINE")
            self._status_label.setObjectName("statusLabel")
            self._chat.add_message(
                "assistant",
                "Memory core reconnected. Full cognitive suite online."
            )
        else:
            self._status_label.setText("● CORE OFFLINE")
            self._status_label.setObjectName("statusLabelOffline")
            self._chat.add_message(
                "assistant",
                "Memory core disconnected. Operating in ephemeral mode."
            )
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)

    def _on_topics_toggled(self, visible: bool):
        self._topics_panel.setVisible(visible)

    def _on_recalls_toggled(self, visible: bool):
        self._recalls_panel.setVisible(visible)

    def _on_search(self):
        text = self._input.get_text()
        if text:
            self._on_send_message(f"smart search {text}", force_search=True)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _update_expression_tag(self, expression: str, speaking: bool):
        if speaking:
            self._expression_tag.setText("● SPEAKING")
        elif expression != "neutral":
            self._expression_tag.setText(f"● {expression.upper()}")
        else:
            self._expression_tag.setText("○ IDLE")
