from __future__ import annotations
from typing import Dict, Optional, Union
from enum import Enum
from PySide6.QtGui import QFontDatabase, QFont
from PySide6.QtWidgets import QAbstractButton

_DEFAULT_FAMILY = "Material Symbols Rounded"

_BUILTIN: Dict[str, str] = {
    "visibility":        "\ue8f4",
    "visibility_off":    "\ue8f5",
    "content_copy":      "\ue14d",
    "content_paste":     "\ue14f",
    "close":             "\ue5cd",
    "check":             "\ue5ca",
    "refresh":           "\ue5d5",
    "settings":          "\ue8b8",
    "search":            "\ue8b6",
    "delete":            "\ue872",
    "add":               "\ue145",
    "remove":            "\ue15b",
    "edit":              "\ue3c9",
    "save":              "\ue161",
    "lock":              "\ue897",
    "lock_open":         "\ue898",
    "warning":           "\ue002",
    "info":              "\ue88e",
    "error":             "\ue000",
}

class Icon(str, Enum):
    visibility = "visibility"
    visibility_off = "visibility_off"
    content_copy = "content_copy"
    content_paste = "content_paste"
    close = "close"
    check = "check"
    refresh = "refresh"
    settings = "settings"
    search = "search"
    delete = "delete"
    add = "add"
    remove = "remove"
    edit = "edit"
    save = "save"
    lock = "lock"
    lock_open = "lock_open"
    warning = "warning"
    info = "info"
    error = "error"

_loaded_family: str = _DEFAULT_FAMILY
_codepoints: Dict[str, str] = dict(_BUILTIN)


def load(ttf_path: Optional[str] = None) -> str:
    global _loaded_family
    if ttf_path:
        fid = QFontDatabase.addApplicationFont(ttf_path)
        if fid != -1:
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                _loaded_family = fams[0]
    return _loaded_family


def family() -> str:
    return _loaded_family


def load_codepoints(codepoints_path: str) -> None:
    global _codepoints
    mapping: Dict[str, str] = {}
    with open(codepoints_path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) != 2:
                continue
            name, hexcp = parts
            try:
                mapping[name] = chr(int(hexcp, 16))
            except ValueError:
                pass
    _codepoints.update(mapping)


def font(size: int = 18) -> QFont:
    f = QFont(_loaded_family)
    f.setPointSize(size)
    return f


def glyph(name: Union[str, Icon], *, fallback: str = "") -> str:
    key = str(name)

    if key:
        return key  # ligature text
    return _codepoints.get(key, fallback)


def apply(button: QAbstractButton, name: Union[str, Icon], *, size: int = 18,
          tooltip: Optional[str] = None) -> None:
    lig = str(name)
    cp = _codepoints.get(lig, "")
    text = lig or cp

    button.setText(text)
    button.setFont(font(size))
    if tooltip is not None:
        button.setToolTip(tooltip)

    cls = button.metaObject().className()
    button.setStyleSheet(f"{cls} {{ font-family: '{_loaded_family}'; border: 0; padding: 0 6px; }}")