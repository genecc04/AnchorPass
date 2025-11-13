from __future__ import annotations
from typing import Optional, Tuple
import re

from PySide6.QtCore import Qt, QRect, QTimer, QEvent
from PySide6.QtGui import ( QFont, QFontDatabase, QPainter, QPixmap, QAction, QColor, QIcon, QPalette )
from PySide6.QtWidgets import QLineEdit, QApplication, QStyle

try:
    from zxcvbn import zxcvbn
    _ZXCVBN = True
except Exception:
    _ZXCVBN = False


def _icon_from_ligature( ligature: str, family: str, point_size: int = 18, padding: int = 2, color: Optional[QColor] = None, ) -> QIcon:

    side = point_size + padding * 2
    screen = QApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0

    pix = QPixmap(int(side * dpr), int(side * dpr))
    pix.setDevicePixelRatio(dpr)
    pix.fill(Qt.transparent)

    font = QFont(family)
    font.setPointSize(point_size)

    if color is None:
        color = QApplication.palette().color(QPalette.ColorRole.ButtonText)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    p.setPen(color)
    p.setFont(font)
    p.drawText(QRect(0, 0, int(side), int(side)), Qt.AlignCenter, ligature)
    p.end()

    return QIcon(pix)

_STRENGTH_COLORS = ["#cc3344", "#ff7a45", "#f2c037", "#80c27a", "#2fa84f"]
_HEURISTIC_RE_CLASSES = re.compile(r"(?P<lower>[a-z])|(?P<upper>[A-Z])|(?P<digit>\d)|(?P<other>\W)")

def _score_with_zxcvbn(pw: str) -> Tuple[int, str]:
    res = zxcvbn(pw)
    score = int(res.get("score", 0))
    label = ["Very weak", "Weak", "Fair", "Strong", "Very strong"][score]
    return score, label

def _score_heuristic(pw: str) -> Tuple[int, str]:
    if not pw:
        return 0, "Very weak"
    length = len(pw)
    classes = set(m.lastgroup for m in _HEURISTIC_RE_CLASSES.finditer(pw) if m.lastgroup)
    classes_count = len(classes)

    base = min(70, length * 5)
    bonus = max(0, (classes_count - 1) * 10)
    pct = max(0, min(100, base + bonus))
    if pct < 25:   score = 0; label = "Very weak"
    elif pct < 50: score = 1; label = "Weak"
    elif pct < 75: score = 2; label = "Fair"
    elif pct < 90: score = 3; label = "Strong"
    else:          score = 4; label = "Very strong"
    return score, label

def _hex_to_rgba_css(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha:.3f})"


class PasswordLineEdit(QLineEdit):
    """
    Parameters:
      placeholder: placeholder text
      clear_clipboard_after_ms: None/0 to disable auto-clear (default 10s)
      icon_point_size: glyph point size (default 20)
      icon_padding: extra pixels around glyph in the square icon (default 2)
      strength_alpha: 0..1 opacity for the tint (default 0.1)
      strength_enabled: toggle strength tinting (default True)
      icon_family: font family already registered in QFontDatabase (e.g., 'Material Symbols Rounded')
      copy_enabled: show/hide the copy-to-clipboard action (default True)
      copy_feedback_ms: milliseconds to show the 'check' icon after copying (default 1200)
      visibility_enabled: show/hide the eye toggle (default True)
    """

    def __init__(
        self,
        placeholder: str = "Password",
        clear_clipboard_after_ms: Optional[int] = 10_000,
        icon_point_size: int = 20,
        icon_padding: int = 2,
        strength_alpha: float = 0.1,
        strength_enabled: bool = True,
        icon_family: Optional[str] = None,
        copy_enabled: bool = True,
        copy_feedback_ms: int = 1200,
        visibility_enabled: bool = True,
        parent=None,
    ):
        super().__init__(parent)

        self.setPlaceholderText(placeholder)
        self.setEchoMode(QLineEdit.Password)
        self.setClearButtonEnabled(True)

        self._clear_ms = clear_clipboard_after_ms
        self._icon_point_size = icon_point_size
        self._icon_padding = icon_padding
        self._strength_alpha = max(0.0, min(1.0, strength_alpha))
        self._strength_enabled = bool(strength_enabled)
        self._copy_enabled = bool(copy_enabled)
        self._copy_feedback_ms = max(0, int(copy_feedback_ms))
        self._visibility_enabled = bool(visibility_enabled)

        self._in_style_update = False
        self._last_css: Optional[str] = None

        self._icon_family: Optional[str] = icon_family
        self._use_ligatures: bool = bool(icon_family and (icon_family in QFontDatabase().families()))

        self._eye_on_icon: QIcon  = QIcon()
        self._eye_off_icon: QIcon = QIcon()
        self._copy_icon: QIcon    = QIcon()
        self._check_icon: QIcon   = QIcon()
        self._build_icons()

        self._eye_action: Optional[QAction] = None
        if self._visibility_enabled:
            self._eye_action = QAction(self._eye_off_icon, "Show password", self)
            self._eye_action.setCheckable(True)
            self._eye_action.triggered.connect(self._toggle_visibility)
            self.addAction(self._eye_action, QLineEdit.TrailingPosition)

        self._copy_action: Optional[QAction] = None
        if self._copy_enabled:
            self._create_copy_action()

        self._copy_feedback_timer = QTimer(self)
        self._copy_feedback_timer.setSingleShot(True)
        self._copy_feedback_timer.timeout.connect(self._reset_copy_icon)

        if self._strength_enabled:
            self.textChanged.connect(self._update_strength_tint)
            self._update_strength_tint(self.text())
        else:
            self._apply_base_stylesheet(None)

        self.textChanged.connect(self._update_copy_visibility)
        self._update_copy_visibility(self.text())

    def setPasswordVisible(self, visible: bool):
        if self._eye_action is not None:
            self._eye_action.setChecked(visible)
        self._apply_visibility(visible)

    def setVisibilityEnabled(self, enabled: bool, *, keep_state: bool = True):
        enabled = bool(enabled)
        if enabled == self._visibility_enabled:
            return

        self._visibility_enabled = enabled

        if enabled:
            if self._eye_action is None:
                self._eye_action = QAction(self._eye_off_icon, "Show password", self)
                self._eye_action.setCheckable(True)
                self._eye_action.triggered.connect(self._toggle_visibility)
            self.addAction(self._eye_action, QLineEdit.TrailingPosition)
            showing = (self.echoMode() == QLineEdit.Normal)
            self._eye_action.setChecked(showing)
            self._apply_visibility(showing)
        else:

            if self._eye_action is not None:
                try:
                    self.removeAction(self._eye_action)
                except Exception:
                    pass

            if not keep_state and self.echoMode() != QLineEdit.Password:
                self.setEchoMode(QLineEdit.Password)

    def isVisibilityEnabled(self) -> bool:
        return self._visibility_enabled

    def setStrengthEnabled(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._strength_enabled:
            return
        self._strength_enabled = enabled

        try:
            self.textChanged.disconnect(self._update_strength_tint)
        except Exception:
            pass
        if enabled:
            self.textChanged.connect(self._update_strength_tint)
            self._update_strength_tint(self.text())
        else:
            self._apply_base_stylesheet(None)

    def setStrengthAlpha(self, alpha: float):
        self._strength_alpha = max(0.0, min(1.0, float(alpha)))
        if self._strength_enabled:
            self._update_strength_tint(self.text())

    def setCopyEnabled(self, enabled: bool):
        enabled = bool(enabled)
        if enabled == self._copy_enabled:
            if enabled:
                self._update_copy_visibility(self.text())
            return

        self._copy_enabled = enabled

        if enabled:
            if self._copy_action is None:
                self._create_copy_action()
            self._update_copy_visibility(self.text())
        else:
            if self._copy_action is not None:
                self._hide_copy_action()
            if self._copy_feedback_timer.isActive():
                self._copy_feedback_timer.stop()

    def setIconFamily(self, family: Optional[str], rebuild: bool = True):
        self._icon_family = family
        self._use_ligatures = bool(family and (family in QFontDatabase().families()))
        if rebuild:
            self._rebuild_icons()

    def _current_fg_color(self) -> QColor:
        pal = self.palette()
        group = QPalette.ColorGroup.Disabled if not self.isEnabled() else QPalette.ColorGroup.Active
        return pal.color(group, QPalette.ColorRole.Text)

    def _build_icons(self):
        if self._use_ligatures and self._icon_family:
            fg = self._current_fg_color()
            self._eye_on_icon  = _icon_from_ligature("visibility_off", self._icon_family,
                                                      point_size=self._icon_point_size,
                                                      padding=self._icon_padding,
                                                      color=fg)
            self._eye_off_icon = _icon_from_ligature("visibility",     self._icon_family,
                                                      point_size=self._icon_point_size,
                                                      padding=self._icon_padding,
                                                      color=fg)
            self._copy_icon    = _icon_from_ligature("content_copy",    self._icon_family,
                                                      point_size=self._icon_point_size,
                                                      padding=self._icon_padding,
                                                      color=fg)
            self._check_icon   = _icon_from_ligature("check",           self._icon_family,
                                                      point_size=self._icon_point_size,
                                                      padding=self._icon_padding,
                                                      color=fg)
        else:
            style = self.style()
            self._eye_on_icon  = style.standardIcon(QStyle.SP_DialogCancelButton)
            self._eye_off_icon = style.standardIcon(QStyle.SP_DialogOkButton)
            self._copy_icon    = style.standardIcon(QStyle.SP_DialogSaveButton)
            self._check_icon   = style.standardIcon(QStyle.SP_DialogApplyButton)

    def _rebuild_icons(self):
        def _do():
            prev_visible = (self.echoMode() == QLineEdit.Normal)
            copy_showing_check = bool(self._copy_action and not self._copy_action.isEnabled())
            self._build_icons()
            if getattr(self, "_eye_action", None):
                self._eye_action.setIcon(self._eye_on_icon if prev_visible else self._eye_off_icon)
            if self._copy_action:
                self._copy_action.setIcon(self._check_icon if copy_showing_check and self._copy_feedback_timer.isActive()
                                          else self._copy_icon)
        QTimer.singleShot(0, _do)

    def _create_copy_action(self):
        self._copy_action = QAction(self._copy_icon, "Copy password", self)
        self._copy_action.triggered.connect(self._copy_to_clipboard)
        self.addAction(self._copy_action, QLineEdit.TrailingPosition)

    def _toggle_visibility(self, checked: bool):
        self._apply_visibility(checked)

    def _apply_visibility(self, visible: bool):
        if visible:
            self.setEchoMode(QLineEdit.Normal)
            if self._eye_action:
                self._eye_action.setIcon(self._eye_on_icon)
                self._eye_action.setText("Hide password")
                self._eye_action.setToolTip("Hide password")
        else:
            self.setEchoMode(QLineEdit.Password)
            if self._eye_action:
                self._eye_action.setIcon(self._eye_off_icon)
                self._eye_action.setText("Show password")
                self._eye_action.setToolTip("Show password")

    def _copy_to_clipboard(self):
        cb = QApplication.clipboard()
        text = self.text()
        cb.setText(text)
        self._show_copy_feedback()
        if self._clear_ms and self._clear_ms > 0:
            def maybe_clear():
                if cb.text() == text:
                    cb.clear()
            QTimer.singleShot(self._clear_ms, maybe_clear)

    def _show_copy_feedback(self):
        if not self._copy_action:
            return
        if self._copy_feedback_timer.isActive():
            self._copy_feedback_timer.stop()
        self._copy_action.setIcon(self._check_icon)
        self._copy_action.setText("Copied")
        self._copy_action.setToolTip("Copied!")
        self._copy_action.setEnabled(False)
        if self._copy_feedback_ms > 0:
            self._copy_feedback_timer.start(self._copy_feedback_ms)
        else:
            self._reset_copy_icon()

    def _reset_copy_icon(self):
        if not self._copy_action:
            return
        self._copy_action.setIcon(self._copy_icon)
        self._copy_action.setText("Copy password")
        self._copy_action.setToolTip("Copy to clipboard")
        self._copy_action.setEnabled(True)

    def _has_action(self, act: QAction) -> bool:
        try:
            return act in self.actions()
        except Exception:
            return False

    def _show_copy_action(self):
        if self._copy_action is None:
            self._create_copy_action()
            return
        if not self._has_action(self._copy_action):
            self.addAction(self._copy_action, QLineEdit.TrailingPosition)
        self._copy_action.setEnabled(True)

    def _hide_copy_action(self):
        if self._copy_action and self._has_action(self._copy_action):
            if self._copy_feedback_timer.isActive():
                self._copy_feedback_timer.stop()
            self._reset_copy_icon()
            try:
                self.removeAction(self._copy_action)
            except Exception:
                pass

    def _update_copy_visibility(self, text: str):
        if not self._copy_enabled:
            return
        if (text or "").strip():
            self._show_copy_action()
        else:
            self._hide_copy_action()

    def _update_strength_tint(self, text: str):
        if not self._strength_enabled:
            self._apply_base_stylesheet(None)
            return

        text = text or ""
        if not text:
            self._apply_base_stylesheet(None)
            return

        try:
            if _ZXCVBN:
                score, _ = _score_with_zxcvbn(text)
            else:
                score, _ = _score_heuristic(text)
        except Exception:
            score = 0

        color_hex = _STRENGTH_COLORS[max(0, min(4, score))]
        rgba = _hex_to_rgba_css(color_hex, self._strength_alpha)
        self._apply_base_stylesheet(rgba)

    def _apply_base_stylesheet(self, rgba_bg: Optional[str]):
        new_css = "" if rgba_bg is None else f"QLineEdit {{ background-color: {rgba_bg}; }}"
        if self._in_style_update or new_css == self._last_css:
            return
        self._in_style_update = True
        try:
            self.setStyleSheet(new_css)
            self._last_css = new_css
        finally:
            self._in_style_update = False

    def changeEvent(self, ev):
        THEME_CHANGE = getattr(QEvent.Type, "ThemeChange", None)
        watched = {
            QEvent.Type.PaletteChange,
            QEvent.Type.ApplicationPaletteChange,
        }
        if THEME_CHANGE is not None:
            watched.add(THEME_CHANGE)

        if ev.type() in watched:
            self._rebuild_icons()
            if self._strength_enabled:
                self._update_strength_tint(self.text())

        super().changeEvent(ev)
