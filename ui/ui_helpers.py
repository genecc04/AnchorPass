from __future__ import annotations
from typing import Optional
from PySide6.QtWidgets import QApplication

_ICON_FAMILY_KEY = "materialSymbols.family"

def set_icon_family(family: Optional[str]) -> None:
    app = QApplication.instance()
    if app is not None:
        app.setProperty(_ICON_FAMILY_KEY, family or "")

def get_icon_family() -> Optional[str]:
    app = QApplication.instance()
    if app is None:
        return None
    fam = app.property(_ICON_FAMILY_KEY)
    fam = str(fam) if fam is not None else ""
    return fam or None
