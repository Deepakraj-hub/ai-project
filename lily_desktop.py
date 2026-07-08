"""
LILY AI — Desktop Application Entry Point
==========================================
Launches the PySide6 desktop application.
Run: python lily_desktop.py
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QIcon, QFont
    from PySide6.QtCore import Qt

    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("LILY AI")
    app.setApplicationDisplayName("LILY — Cognitive AI Core")
    app.setOrganizationName("LILY AI")

    # Set default font
    font = QFont("Segoe UI", 10)
    font.setStyleStrategy(QFont.PreferAntialias)
    app.setFont(font)

    # Dark palette for native dialogs
    from PySide6.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(6, 6, 16))
    palette.setColor(QPalette.WindowText, QColor(241, 245, 249))
    palette.setColor(QPalette.Base, QColor(12, 12, 26))
    palette.setColor(QPalette.AlternateBase, QColor(17, 17, 37))
    palette.setColor(QPalette.Text, QColor(241, 245, 249))
    palette.setColor(QPalette.Button, QColor(17, 17, 37))
    palette.setColor(QPalette.ButtonText, QColor(241, 245, 249))
    palette.setColor(QPalette.Highlight, QColor(168, 85, 247))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipBase, QColor(17, 17, 37))
    palette.setColor(QPalette.ToolTipText, QColor(241, 245, 249))
    app.setPalette(palette)

    # Launch main window
    from lily_window import LilyWindow
    window = LilyWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
