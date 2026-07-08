"""
InputWidget — Text input field with voice button and send button.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton


class InputWidget(QWidget):
    """Chat input area with text field, voice toggle, and send button."""

    message_sent = Signal(str)
    voice_toggled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Text input
        self._input = QLineEdit()
        self._input.setObjectName("chatInput")
        self._input.setPlaceholderText("Ask LILY anything...")
        self._input.returnPressed.connect(self._on_send)
        layout.addWidget(self._input)

        # Voice button
        self._voice_btn = QPushButton("🎤")
        self._voice_btn.setObjectName("voiceBtn")
        self._voice_btn.setCursor(Qt.PointingHandCursor)
        self._voice_btn.clicked.connect(self._on_voice)
        layout.addWidget(self._voice_btn)

        # Send button
        self._send_btn = QPushButton("SEND")
        self._send_btn.setObjectName("sendBtn")
        self._send_btn.setCursor(Qt.PointingHandCursor)
        self._send_btn.clicked.connect(self._on_send)
        layout.addWidget(self._send_btn)

        self._is_listening = False

    def _on_send(self):
        text = self._input.text().strip()
        if text:
            self.message_sent.emit(text)
            self._input.clear()

    def _on_voice(self):
        self.voice_toggled.emit()

    def set_listening(self, listening: bool):
        self._is_listening = listening
        if listening:
            self._voice_btn.setText("🔴")
            self._voice_btn.setObjectName("voiceBtnActive")
            self._input.setPlaceholderText("🎤  Listening...")
        else:
            self._voice_btn.setText("🎤")
            self._voice_btn.setObjectName("voiceBtn")
            self._input.setPlaceholderText("Ask LILY anything...")
        self._voice_btn.style().unpolish(self._voice_btn)
        self._voice_btn.style().polish(self._voice_btn)

    def set_enabled(self, enabled: bool):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)

    def set_text(self, text: str):
        self._input.setText(text)

    def get_text(self) -> str:
        return self._input.text().strip()

    def focus_input(self):
        self._input.setFocus()
