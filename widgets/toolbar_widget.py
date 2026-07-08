"""
ToolbarWidget — Row of action buttons: Memory, Topics, Recalls, Search.
"""

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QSizePolicy


class ToolbarWidget(QWidget):
    """Toolbar with Memory, Topics, Recalls, Search buttons."""

    memory_toggled = Signal(bool)
    topics_toggled = Signal(bool)
    recalls_toggled = Signal(bool)
    search_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Memory button
        self._memory_on = True
        self._memory_btn = QPushButton("● MEMORY")
        self._memory_btn.setObjectName("memoryBtnOn")
        self._memory_btn.setCursor(Qt.PointingHandCursor)
        self._memory_btn.clicked.connect(self._toggle_memory)
        layout.addWidget(self._memory_btn)

        # Topics toggle
        self._topics_btn = QPushButton("📋 TOPICS")
        self._topics_btn.setObjectName("toolbarBtn")
        self._topics_btn.setCheckable(True)
        self._topics_btn.setCursor(Qt.PointingHandCursor)
        self._topics_btn.toggled.connect(self.topics_toggled.emit)
        layout.addWidget(self._topics_btn)

        # Recalls toggle
        self._recalls_btn = QPushButton("🔄 RECALLS")
        self._recalls_btn.setObjectName("toolbarBtn")
        self._recalls_btn.setCheckable(True)
        self._recalls_btn.setCursor(Qt.PointingHandCursor)
        self._recalls_btn.toggled.connect(self.recalls_toggled.emit)
        layout.addWidget(self._recalls_btn)

        # Search button
        self._search_btn = QPushButton("🔍 SEARCH")
        self._search_btn.setObjectName("searchBtn")
        self._search_btn.setCursor(Qt.PointingHandCursor)
        self._search_btn.clicked.connect(self.search_clicked.emit)
        layout.addWidget(self._search_btn)

        layout.addStretch()



    def _toggle_memory(self):
        self._memory_on = not self._memory_on
        if self._memory_on:
            self._memory_btn.setText("● MEMORY")
            self._memory_btn.setObjectName("memoryBtnOn")
        else:
            self._memory_btn.setText("○ MEMORY")
            self._memory_btn.setObjectName("memoryBtnOff")
        # Force style refresh
        self._memory_btn.style().unpolish(self._memory_btn)
        self._memory_btn.style().polish(self._memory_btn)
        self.memory_toggled.emit(self._memory_on)

    def update_topic_count(self, count: int):
        text = f"📋 TOPICS ({count})" if count > 0 else "📋 TOPICS"
        self._topics_btn.setText(text)

    def update_recall_count(self, count: int):
        text = f"🔄 RECALLS ({count})" if count > 0 else "🔄 RECALLS"
        self._recalls_btn.setText(text)

    def set_search_enabled(self, enabled: bool):
        self._search_btn.setEnabled(enabled)

    @property
    def is_memory_connected(self):
        return self._memory_on
