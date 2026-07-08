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
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage


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

        # ── Start Local Web Server ──
        self._port = get_free_port()
        self._dist_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "ai-avatar", "dist"
        )
        self._start_server()

        # ── Setup Web View ──
        profile = QWebEngineProfile.defaultProfile()
        # Enable WebGL
        self._web_view = QWebEngineView(self)
        
        # Make background transparent
        self._web_view.page().setBackgroundColor(Qt.transparent)
        
        self._layout.addWidget(self._web_view)

        # Load the local server URL
        self._web_view.setUrl(QUrl(f"http://localhost:{self._port}/"))

        self._expression = "neutral"
        self._is_talking = False

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

    def set_expression(self, expression: str):
        self._expression = expression.lower()
        self._web_view.page().runJavaScript(f"if (window.setAvatarExpression) window.setAvatarExpression('{self._expression}');")

    def set_talking(self, talking: bool):
        self._is_talking = talking
        self._web_view.page().runJavaScript(f"if (window.setAvatarTalking) window.setAvatarTalking({'true' if talking else 'false'});")

    def closeEvent(self, event):
        if hasattr(self, '_httpd'):
            self._httpd.shutdown()
        super().closeEvent(event)
