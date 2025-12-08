from __future__ import annotations
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QCoreApplication

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow

from helpers.app_utils import (
    load_styles,
    load_material_symbols_once,
    SingleInstanceApp
)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AnchorPass")
    QCoreApplication.setApplicationName("AnchorPass")
    single_instance = SingleInstanceApp("AnchorPass_SingleInstance")
    if single_instance.is_running():
        sys.exit(0)
    
    ok, fontfam = load_material_symbols_once()

    sm = SettingsManager()
    theme = sm.get("theme", "dark")
    load_styles(app, theme)

    w = MainWindow(icon_family=fontfam if ok else "")
    
    single_instance.set_main_window(w)
    
    w.show()
    app.exec()

if __name__ == "__main__":
    main()