from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from ui import material_symbols as ms

BASE_DIR = Path(
    getattr(
        sys,
        "_MEIPASS",
        Path(__file__).resolve().parent.parent
    )
)


def resource_path(relative: str | Path) -> Path:
    return BASE_DIR / Path(relative)


def load_styles(app: QApplication, theme: str) -> None:
    app.setStyle(QStyleFactory.create("Fusion"))
    qss_parts: list[str] = []

    base_qss = resource_path("styles/base.qss")
    theme_qss = resource_path(f"styles/{theme}.qss")

    if base_qss.exists():
        qss_parts.append(base_qss.read_text(encoding="utf-8"))

    if theme_qss.exists():
        qss_parts.append(theme_qss.read_text(encoding="utf-8"))

    app.setStyleSheet("\n".join(qss_parts))


def load_material_symbols_once() -> Tuple[bool, str]:
    candidates = [
        resource_path("assets/icons/MaterialSymbolsRounded.ttf"),
        Path(__file__).resolve().parent.parent / "assets" / "icons" / "MaterialSymbolsRounded.ttf",
    ]

    for p in candidates:
        try:
            if p.exists():
                fam = ms.load(str(p))
                if fam:
                    return True, fam
        except Exception:
            pass

    try:
        fam = ms.load(None)
        if fam:
            return True, fam
    except Exception:
        pass

    return False, ""

class SingleInstanceApp:
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.server = None
        self.main_window = None
        
    def is_running(self) -> bool:
        """Check if another instance is already running."""
        socket = QLocalSocket()
        socket.connectToServer(self.app_id)
        
        if socket.waitForConnected(500):
            socket.write(b"ACTIVATE")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return True
        
        self.server = QLocalServer()
        QLocalServer.removeServer(self.app_id)
        
        if not self.server.listen(self.app_id):
            return True
        
        self.server.newConnection.connect(self._on_new_connection)
        return False
    
    def set_main_window(self, window):
        """Set the main window reference for activation."""
        self.main_window = window
    
    def _on_new_connection(self):
        """Handle connection from new instance attempting to start."""
        if not self.server:
            return
            
        socket = self.server.nextPendingConnection()
        if socket and socket.waitForReadyRead(1000):
            message = socket.readAll().data()
            if message == b"ACTIVATE" and self.main_window:
                self._activate_window()
    
    def _activate_window(self):
        """Bring the main window to front and activate it."""
        if not self.main_window:
            return
        
        if self.main_window.isMinimized():
            self.main_window.showNormal()
        
        self.main_window.raise_()
        self.main_window.activateWindow()
        self.main_window.show()