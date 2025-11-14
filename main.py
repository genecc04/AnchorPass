from __future__ import annotations

import sys
from PySide6.QtWidgets import QApplication

from core.settings_manager import SettingsManager
from ui.main_window import MainWindow

from helpers.app_utils import (
    load_styles,
    load_material_symbols_once,
)


def main():
    app = QApplication(sys.argv)

    ok, fontfam = load_material_symbols_once()

    sm = SettingsManager()
    theme = sm.get("theme", "dark")
    load_styles(app, theme)

    w = MainWindow(icon_family=fontfam if ok else "")
    w.show()
    app.exec()


if __name__ == "__main__":
    main()