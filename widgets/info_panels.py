"""
InfoPanels — Topics and Recalls collapsible panels,
and Search results banner.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QSizePolicy
)


class TopicsPanel(QFrame):
    """Displays extracted conversation topics as tags."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("infoPanel")
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(6)

        header = QLabel("▸ TOPICS")
        header.setObjectName("infoPanelLabel")
        self._layout.addWidget(header)

        self._tags_layout = QHBoxLayout()
        self._tags_layout.setSpacing(6)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)

        tags_container = QWidget()
        tags_container.setLayout(self._tags_layout)
        self._layout.addWidget(tags_container)

        self._tags_layout.addStretch()

    def update_topics(self, topics: list):
        # Clear old tags (keep stretch)
        while self._tags_layout.count() > 1:
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for topic in topics[-10:]:
            tag = QLabel(f"#{topic}")
            tag.setObjectName("topicTag")
            self._tags_layout.insertWidget(self._tags_layout.count() - 1, tag)


class RecallsPanel(QFrame):
    """Displays extracted recalls."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("infoPanel")
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(4)

        header = QLabel("▸ RECALLS")
        header.setObjectName("infoPanelLabel")
        self._layout.addWidget(header)

    def update_recalls(self, recalls: list):
        # Remove old items (keep header)
        while self._layout.count() > 1:
            item = self._layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        for recall in recalls[-10:]:
            item = QLabel(f"↳ {recall}")
            item.setObjectName("recallItem")
            item.setWordWrap(True)
            self._layout.addWidget(item)


class SearchBanner(QFrame):
    """Displays smart search results banner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("searchBanner")
        self.setVisible(False)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(10, 8, 10, 8)
        self._layout.setSpacing(4)

        self._title = QLabel()
        self._title.setObjectName("searchBannerTitle")
        self._layout.addWidget(self._title)

    def show_results(self, query: str, mode: str, sources: list):
        # Clear old sources
        while self._layout.count() > 1:
            item = self._layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        self._title.setText(f"▸ SEARCH ({mode or 'web'}) — {query}")

        for source in sources[:3]:
            src_label = QLabel(f"↳ {source.get('title', '')}")
            src_label.setObjectName("searchSource")
            src_label.setWordWrap(True)
            self._layout.addWidget(src_label)

        self.setVisible(True)

    def hide_results(self):
        self.setVisible(False)
