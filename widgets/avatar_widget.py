"""
AvatarWidget — Web-based 3D avatar embedded via QWebEngineView.
Runs a local HTTP server to serve the built React app containing the 3D model.
"""

import threading
import http.server
import socketserver
import os
import socket

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    _WEBENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    QWebEngineProfile = None
    QWebEnginePage = None
    _WEBENGINE_AVAILABLE = False


def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class AvatarWidget(QWidget):
    """Embeds the 3D Avatar React app via QWebEngineView."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(300, 300)

        # ── Setup Layout ──
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self._expression = "neutral"
        self._is_talking = False
        self._fallback_label = None
        self._web_view = None

        # ── Start Local Web Server ──
        self._port = get_free_port()
        self._dist_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ai-avatar", "dist"
        )
        self._start_server()

        # ── Setup Web View or graceful fallback ──
        if _WEBENGINE_AVAILABLE and os.path.isdir(self._dist_dir):
            try:
                profile = QWebEngineProfile.defaultProfile()
                self._web_view = QWebEngineView(self)
                self._layout.addWidget(self._web_view)
                self._web_view.setUrl(QUrl(f"http://localhost:{self._port}/"))
            except Exception as exc:
                print(f"[Avatar] WebEngine fallback enabled: {exc}")
                self._enable_fallback_ui()
        else:
            self._enable_fallback_ui()

    def _start_server(self):
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=self.directory, **kwargs)

            def log_message(self, format, *args):
                pass  # suppress logs

        Handler.directory = self._dist_dir

        self._httpd = socketserver.TCPServer(("", self._port), Handler)
        self._server_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._server_thread.start()

    def _enable_fallback_ui(self):
        self._fallback_label = QLabel("LILY\nCinematic interface ready")
        self._fallback_label.setAlignment(Qt.AlignCenter)
        self._fallback_label.setWordWrap(True)
        self._fallback_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 4px;
            color: #f8fafc;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #111827, stop:1 #312e81);
            border: 1px solid rgba(192, 132, 252, 0.35);
            border-radius: 16px;
            padding: 32px;
        """)
        self._layout.addWidget(self._fallback_label)

    def set_expression(self, expression: str):
        self._expression = expression.lower()
        if self._web_view is not None and hasattr(self._web_view, 'page'):
            self._web_view.page().runJavaScript(f"if (window.setAvatarExpression) window.setAvatarExpression('{self._expression}');")
        if self._fallback_label is not None:
            label_text = self._expression.upper()
            self._fallback_label.setText(f"LILY\n{label_text}")

    def set_talking(self, talking: bool):
        self._is_talking = talking
        if self._web_view is not None and hasattr(self._web_view, 'page'):
            self._web_view.page().runJavaScript(f"if (window.setAvatarTalking) window.setAvatarTalking({'true' if talking else 'false'});")
        if self._fallback_label is not None:
            status = "SPEAKING" if talking else "LISTENING"
            self._fallback_label.setText(f"LILY\n{status}")

    def closeEvent(self, event):
        if hasattr(self, '_httpd'):
            self._httpd.shutdown()
        super().closeEvent(event)
