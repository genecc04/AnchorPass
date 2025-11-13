from __future__ import annotations
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QStyleFactory
from core.settings_manager import SettingsManager
from ui.main_window import MainWindow
from ui import material_symbols as ms

def resource_path(relative: str | Path) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / Path(relative)

def load_styles(app: QApplication, theme: str):
    app.setStyle(QStyleFactory.create("Fusion"))
    qss = ""

    base_qss = resource_path("styles/base.qss")
    theme_qss = resource_path(f"styles/{theme}.qss")

    if base_qss.exists():
        qss += base_qss.read_text(encoding="utf-8")
    if theme_qss.exists():
        qss += "\n" + theme_qss.read_text(encoding="utf-8")

    app.setStyleSheet(qss)

def load_material_symbols_once() -> tuple[bool, str]:
    candidates = [
        resource_path("assets/icons/MaterialSymbolsRounded.ttf"),
        Path(__file__).resolve().parent / "assets" / "icons" / "MaterialSymbolsRounded.ttf",
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
