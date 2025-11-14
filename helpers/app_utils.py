from __future__ import annotations

import sys
from pathlib import Path
from typing import Tuple

from PySide6.QtWidgets import QApplication, QStyleFactory
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
