"""
AudioVisualizer — Voice waveform visualizer with microphone icon and flowing waves.
Replaces bars with sophisticated waveform animation responding to speech state.
"""

import math
import time
import random
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QPainter, QColor, QPen, QLinearGradient, QRadialGradient, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget


class AudioVisualizerBars(QWidget):
    """Flowing waveform visualizer with microphone icon."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 300)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        
        # Animation state
        self._waveforms = []
        self._time_offset = 0.0
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._animate_waveforms)
        self._anim_timer.start(30)  # 30ms tick for smooth animation
        
        # State tracking
        self._is_talking = False
        self._is_listening = False
        self._expression = "neutral"
        
        # Expression color schemes (start_color, end_color)
        self._expression_colors = {
            "smiling": ((147, 51, 234), (34, 197, 94)),      # purple → green
            "sad": ((59, 130, 246), (34, 211, 238)),         # blue → cyan
            "angry": ((239, 68, 68), (234, 179, 8)),         # red → yellow
            "shy": ((236, 72, 153), (147, 51, 234)),         # pink → purple
            "neutral": ((99, 102, 241), (79, 70, 229)),      # indigo → deeper indigo
        }
        
        # Generate initial waveforms
        self._generate_waveforms()

    def set_talking(self, talking: bool):
        """Update talking state (high motion)."""
        self._is_talking = talking
        self._is_listening = not talking

    def set_expression(self, expression: str):
        """Set expression (smiling/sad/angry/shy/neutral)."""
        self._expression = expression.lower()
        if self._expression not in self._expression_colors:
            self._expression = "neutral"

    def _generate_waveforms(self):
        """Generate multiple waveform layers."""
        self._waveforms = []
        num_waves = 5
        for i in range(num_waves):
            self._waveforms.append({
                'phase': random.uniform(0, 2 * math.pi),
                'frequency': 0.5 + i * 0.3,
                'amplitude': 0.3 + i * 0.15,
            })

    def _animate_waveforms(self):
        """Animate waveforms based on state."""
        if self._is_talking:
            self._time_offset += 0.08  # Faster for talking
        elif self._is_listening:
            self._time_offset += 0.04  # Medium speed for listening
        else:
            self._time_offset += 0.02  # Slow for idle
        
        # Modulate waveform amplitudes based on state
        for i, wave in enumerate(self._waveforms):
            if self._is_talking:
                wave['amplitude'] = 0.4 + i * 0.15 + random.uniform(-0.05, 0.15)
            elif self._is_listening:
                wave['amplitude'] = 0.2 + i * 0.08 + random.uniform(-0.02, 0.05)
            else:
                wave['amplitude'] = 0.1 + i * 0.04 + random.uniform(-0.01, 0.02)
        
        self.update()

    def paintEvent(self, event):
        """Render the flowing waveform visualizer."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        
        w = self.width()
        h = self.height()
        
        # Gradient background
        bg_gradient = QLinearGradient(0, 0, w, h)
        bg_gradient.setColorAt(0, QColor(10, 14, 32))
        bg_gradient.setColorAt(1, QColor(15, 13, 25))
        painter.fillRect(self.rect(), bg_gradient)
        
        # Draw microphone icon at top
        self._draw_microphone_icon(painter, w, h)
        
        # Draw waveforms
        self._draw_waveforms(painter, w, h)
        
        painter.end()

    def _draw_microphone_icon(self, painter, w, h):
        """Draw microphone icon at the top center."""
        icon_x = w // 2
        icon_y = h // 5
        icon_size = 40
        
        # Outer circle (glow)
        painter.setBrush(QBrush(QColor(99, 102, 241, 30)))
        painter.setPen(QPen(QColor(99, 102, 241, 60), 2))
        painter.drawEllipse(icon_x - icon_size, icon_y - icon_size, icon_size * 2, icon_size * 2)
        
        # Middle circle
        painter.setBrush(QBrush(QColor(79, 70, 229, 60)))
        painter.setPen(QPen(QColor(99, 102, 241, 120), 2))
        painter.drawEllipse(icon_x - int(icon_size * 0.7), icon_y - int(icon_size * 0.7), 
                           int(icon_size * 1.4), int(icon_size * 1.4))
        
        # Inner microphone symbol (gradient circle)
        mic_rad = int(icon_size * 0.35)
        mic_gradient = QRadialGradient(icon_x, icon_y, mic_rad)
        mic_gradient.setColorAt(0, QColor(147, 51, 234, 200))
        mic_gradient.setColorAt(1, QColor(79, 70, 229, 255))
        painter.setBrush(mic_gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(icon_x, icon_y), mic_rad, mic_rad)
        
        # Microphone icon (simple outline)
        painter.setPen(QPen(QColor(200, 200, 255, 255), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        # Microphone capsule
        painter.drawRect(icon_x - 6, icon_y - 10, 12, 14)
        # Microphone stand
        painter.drawLine(icon_x, icon_y + 4, icon_x, icon_y + 12)

    def _draw_waveforms(self, painter, w, h):
        """Draw flowing waveforms."""
        get_colors = self._expression_colors.get(self._expression, self._expression_colors["neutral"])
        
        waveform_y_center = h * 0.55
        waveform_width = w * 0.7
        waveform_start_x = (w - waveform_width) // 2
        
        # Draw each waveform layer
        for layer_idx, wave in enumerate(self._waveforms):
            # Calculate color interpolation
            t = layer_idx / max(1, len(self._waveforms) - 1)
            r = int(get_colors[0][0] * (1 - t) + get_colors[1][0] * t)
            g = int(get_colors[0][1] * (1 - t) + get_colors[1][1] * t)
            b = int(get_colors[0][2] * (1 - t) + get_colors[1][2] * t)
            
            # Alpha decreases with layer depth
            alpha = int(200 * (1 - layer_idx * 0.15))
            
            path = QPainterPath()
            
            # Generate waveform points
            num_points = int(waveform_width / 2)
            points = []
            
            for x_idx in range(num_points):
                x = waveform_start_x + (x_idx / num_points) * waveform_width
                
                # Combine multiple sine waves for complex motion
                phase = self._time_offset + wave['phase']
                sine_val = math.sin(x_idx * wave['frequency'] * 0.02 + phase)
                
                # Add harmonic variations
                sine_val += 0.3 * math.sin(x_idx * wave['frequency'] * 0.04 + phase * 0.5)
                sine_val += 0.15 * math.sin(x_idx * wave['frequency'] * 0.08 + phase * 0.25)
                
                y_offset = sine_val * wave['amplitude'] * h * 0.25
                y = waveform_y_center + y_offset
                
                points.append((x, y))
            
            # Create smooth path
            if points:
                path.moveTo(int(points[0][0]), int(points[0][1]))
                for i in range(1, len(points)):
                    path.lineTo(int(points[i][0]), int(points[i][1]))
            
            # Draw waveform with gradient stroke
            painter.setPen(QPen(QColor(r, g, b, alpha), 3))
            painter.drawPath(path)
            
            # Optional: Fill area under wave for depth
            if layer_idx == len(self._waveforms) - 1:
                # Close path for fill
                if points:
                    path.lineTo(int(points[-1][0]), int(waveform_y_center + h * 0.1))
                    path.lineTo(int(points[0][0]), int(waveform_y_center + h * 0.1))
                    path.closeSubpath()
                    painter.setBrush(QBrush(QColor(r, g, b, 20)))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawPath(path)
