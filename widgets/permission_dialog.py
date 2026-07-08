"""Permission approval dialog for Lily agent actions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTextEdit,
    QVBoxLayout,
)


class PermissionDialog(QDialog):
    """Modal approval card shown before Lily runs a risky tool action."""

    def __init__(self, request: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LILY — Permission Required")
        self.setModal(True)
        self.setMinimumWidth(520)
        self._always_allow = False

        layout = QVBoxLayout(self)
        layout.setSpacing(14)

        title = QLabel("Lily wants to perform an action")
        title.setObjectName("permissionTitle")
        layout.addWidget(title)

        risk = request.get("risk_level", "unknown").upper()
        risk_label = QLabel(f"Risk level: {risk}")
        risk_label.setObjectName("permissionRisk")
        layout.addWidget(risk_label)

        action = request.get("action", "Unknown action")
        reason = request.get("reason", "No reason provided.")
        tool = request.get("tool_name", "agent")

        info = QLabel(f"<b>Tool:</b> {tool}<br><b>Action:</b> {action}<br><br>{reason}")
        info.setWordWrap(True)
        info.setTextFormat(Qt.RichText)
        layout.addWidget(info)

        files = request.get("affected_files") or []
        if files:
            files_box = QTextEdit()
            files_box.setReadOnly(True)
            files_box.setMaximumHeight(90)
            files_box.setPlainText("\n".join(files))
            layout.addWidget(QLabel("Affected paths:"))
            layout.addWidget(files_box)

        params = request.get("parameters") or {}
        if params:
            preview = QTextEdit()
            preview.setReadOnly(True)
            preview.setMaximumHeight(120)
            preview.setPlainText(self._format_params(params))
            layout.addWidget(QLabel("Parameters:"))
            layout.addWidget(preview)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        self._always_cb = QCheckBox("Always allow this type of action for this session")
        layout.addWidget(self._always_cb)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Allow")
        buttons.button(QDialogButtonBox.Cancel).setText("Deny")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog { background: #0c0c1a; color: #e2e8f0; }
            QLabel#permissionTitle { font-size: 18px; font-weight: 700; color: #c084fc; }
            QLabel#permissionRisk { color: #fbbf24; font-weight: 600; }
            QTextEdit { background: #111827; border: 1px solid #334155; border-radius: 6px; color: #cbd5e1; }
            QCheckBox { color: #94a3b8; }
            QPushButton { padding: 8px 16px; border-radius: 6px; }
        """)

    def _format_params(self, params: dict) -> str:
        lines = []
        for key, value in params.items():
            if key == "content" and isinstance(value, str) and len(value) > 400:
                lines.append(f"{key}: <{len(value)} chars of content>")
            else:
                lines.append(f"{key}: {value}")
        return "\n".join(lines)

    @property
    def always_allow(self) -> bool:
        return self._always_cb.isChecked()
