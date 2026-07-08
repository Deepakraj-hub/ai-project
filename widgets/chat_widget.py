"""
ChatWidget — Scrollable chat message display with styled bubbles.
"""

from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QSizePolicy, QGraphicsOpacityEffect
)


class MessageBubble(QFrame):
    """A single chat message bubble."""

    def __init__(self, role: str, content: str, parent=None):
        super().__init__(parent)
        self.setObjectName("msgLily" if role == "assistant" else "msgUser")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        # Role label
        role_label = QLabel("◈ LILY" if role == "assistant" else "▸ YOU")
        role_label.setObjectName("roleLily" if role == "assistant" else "roleUser")
        layout.addWidget(role_label)

        # Message text
        text_label = QLabel(content)
        text_label.setObjectName("msgText")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(text_label)

        # Entrance animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        self._anim = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._anim.setDuration(300)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        # Defer start to next event loop tick so widget is laid out
        QTimer.singleShot(10, self._anim.start)


class ThinkingIndicator(QFrame):
    """Animated 'thinking' dots indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        self._dots = []
        for i in range(3):
            dot = QLabel("●")
            dot.setStyleSheet(f"""
                font-size: 8px;
                color: rgba(168, 85, 247, {80 + i * 50});
            """)
            layout.addWidget(dot)
            self._dots.append(dot)

        label = QLabel("  Lily is thinking...")
        label.setObjectName("thinkingLabel")
        layout.addWidget(label)
        layout.addStretch()

        # Dot animation
        self._phase = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate_dots)
        self._timer.start(400)

    def _animate_dots(self):
        self._phase = (self._phase + 1) % 3
        for i, dot in enumerate(self._dots):
            alpha = 220 if i == self._phase else 60
            dot.setStyleSheet(f"font-size: 8px; color: rgba(168, 85, 247, {alpha});")


class ChatWidget(QWidget):
    """Scrollable chat display area with auto-scroll."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setObjectName("chatScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Content widget
        self._content = QWidget()
        self._content.setObjectName("chatContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(6)
        self._content_layout.addStretch()

        self._scroll.setWidget(self._content)
        layout.addWidget(self._scroll)

        self._thinking = None

    def add_message(self, role: str, content: str):
        """Add a new message bubble."""
        self.hide_thinking()
        bubble = MessageBubble(role, content, self._content)
        # Insert before the stretch
        self._content_layout.insertWidget(
            self._content_layout.count() - 1, bubble
        )
        # Auto-scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

    def show_thinking(self):
        """Show the thinking indicator."""
        if self._thinking is None:
            self._thinking = ThinkingIndicator(self._content)
            self._content_layout.insertWidget(
                self._content_layout.count() - 1, self._thinking
            )
            QTimer.singleShot(50, self._scroll_to_bottom)

    def hide_thinking(self):
        """Hide and remove the thinking indicator."""
        if self._thinking is not None:
            self._content_layout.removeWidget(self._thinking)
            self._thinking.deleteLater()
            self._thinking = None

    def _scroll_to_bottom(self):
        sb = self._scroll.verticalScrollBar()
        sb.setValue(sb.maximum())
