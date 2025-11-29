from __future__ import annotations
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor


def load_styles(app: QApplication, theme: str = "dark", extra_qss: Optional[str] = None) -> None:
    base = Path(__file__).with_name("base.qss")
    theme_file = Path(__file__).with_name(f"{theme}.qss")

    qss_parts: list[str] = []
    if base.exists():
        qss_parts.append(base.read_text(encoding="utf-8"))
    if theme_file.exists():
        qss_parts.append(theme_file.read_text(encoding="utf-8"))
    if extra_qss:
        qss_parts.append(extra_qss)

    app.setStyleSheet("\n\n".join(qss_parts))

    palette = app.palette()

    if theme.lower() == "dark":
        link = QColor("#4ea1ff")       # normal link
        visited = QColor("#82b1ff")    # visited link (optional)
    else:
        # light theme defaults
        link = QColor("#1565c0")
        visited = QColor("#0d47a1")

    palette.setColor(QPalette.Link, link)
    palette.setColor(QPalette.LinkVisited, visited)
    app.setPalette(palette)
