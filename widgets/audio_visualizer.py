"""
AudioVisualizer — Premium animated audio bars that respond to Lily's speech state.
"""

import random
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QPainter, QColor, QLinearGradient
from PySide6.QtWidgets import QWidget


class AudioVisualizerBars(QWidget):
    """Animated equalizer-style audio bars."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(120)
        self.setMinimumWidth(200)
        self.setStyleSheet("background: transparent;")

        # State
        self._is_talking = False
        self._is_listening = False
        self._bars_count = 12
        self._bar_heights = [0.1] * self._bars_count
        self._target_heights = [0.1] * self._bars_count
        self._expression = "neutral"

        # Animation timer
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._animate_bars)
        self._anim_timer.start(50)

    def set_talking(self, talking: bool):
        self._is_talking = talking
        self._is_listening = not talking

    def set_expression(self, expression: str):
        self._expression = expression.lower()

    def _animate_bars(self):
        """Smoothly animate bar heights based on state."""
        if self._is_talking:
            # Talking: bars move up and down dynamically
            for i in range(self._bars_count):
                self._target_heights[i] = random.uniform(0.3, 0.95)
        elif self._is_listening:
            # Listening: subtle gentle motion
            for i in range(self._bars_count):
                self._target_heights[i] = random.uniform(0.15, 0.35)
        else:
            # Idle: minimal motion
            for i in range(self._bars_count):
                self._target_heights[i] = random.uniform(0.08, 0.15)

        # Smooth interpolation toward target heights
        for i in range(self._bars_count):
            self._bar_heights[i] += (self._target_heights[i] - self._bar_heights[i]) * 0.15

        self.update()

    def paintEvent(self, event):
        """Draw the animated bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Canvas dimensions
        w = self.width()
        h = self.height()

        # Background gradient
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0, QColor(6, 10, 20))
        bg_grad.setColorAt(1, QColor(15, 12, 25))
        painter.fillRect(self.rect(), bg_grad)

        # Draw bars
        bar_width = max(6, (w - (self._bars_count - 1) * 12) // self._bars_count)
        spacing = 12
        start_x = (w - (self._bars_count * bar_width + (self._bars_count - 1) * spacing)) // 2

        for i in range(self._bars_count):
            x = start_x + i * (bar_width + spacing)
            bar_height = self._bar_heights[i] * (h - 40)
            y = h - 20 - bar_height

            # Gradient for each bar (purple to cyan)
            bar_grad = QLinearGradient(x, h - 20, x, y)
            if self._expression == "smiling":
                bar_grad.setColorAt(0, QColor(168, 85, 247))  # purple
                bar_grad.setColorAt(1, QColor(34, 211, 238))  # cyan
            elif self._expression == "sad":
                bar_grad.setColorAt(0, QColor(59, 130, 246))  # blue
                bar_grad.setColorAt(1, QColor(45, 212, 191))  # teal
            elif self._expression == "angry":
                bar_grad.setColorAt(0, QColor(244, 63, 94))  # red
                bar_grad.setColorAt(1, QColor(251, 146, 60))  # orange
            elif self._expression == "shy":
                bar_grad.setColorAt(0, QColor(236, 72, 153))  # pink
                bar_grad.setColorAt(1, QColor(168, 85, 247))  # purple
            else:  # neutral
                bar_grad.setColorAt(0, QColor(192, 132, 252))  # violet
                bar_grad.setColorAt(1, QColor(99, 102, 241))  # indigo

            painter.fillRect(x, y, bar_width, bar_height, bar_grad)

            # Subtle glow at the top
            glow_color = QColor(99, 102, 241, 100)
            painter.fillRect(x, y - 2, bar_width, 2, glow_color)

        painter.end()
