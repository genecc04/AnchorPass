from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import ( QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPlainTextEdit, QSizePolicy, QSplitter )
from PySide6.QtGui import QFont

from core.settings_manager import SettingsManager
from core import db
from core import totp as totp_util
from ui.widgets.totp_ring import TotpRingWidget

try:
    from core import db_crypto as dbx
except Exception:
    dbx = None


EMPTY_MESSAGE = "No record selected. Please select a record to view it here."

_CHAR_LIMITS = {
    "site": 55,
    "email": 55,
    "username": 55,
    "site_link": 55,
    "notes": 1024,
    "totp": 32,
}


def _limit_text(text: str, key: str) -> tuple[str, str]:
    if text is None:
        return "—", ""
    s = str(text)
    if not s:
        return "—", ""
    limit = _CHAR_LIMITS.get(key, 0)
    if limit and len(s) > limit:
        return s[:limit].rstrip() + "…", s
    return s, s


class _PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(8)

        self.empty_msg = QLabel(EMPTY_MESSAGE, self)
        self.empty_msg.setAlignment(Qt.AlignCenter)
        self.empty_msg.setWordWrap(True)
        fmsg = QFont()
        fmsg.setPointSize(11)
        self.empty_msg.setFont(fmsg)
        self.empty_msg.setVisible(False)
        root.addWidget(self.empty_msg)

        self.details_wrap = QWidget(self)
        details = QVBoxLayout(self.details_wrap)
        details.setContentsMargins(0, 0, 0, 0)
        details.setSpacing(8)
        root.addWidget(self.details_wrap)

        self.title = QLabel("—")
        self.title.setTextFormat(Qt.PlainText)
        self.title.setWordWrap(True)
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self.title.setFont(f)
        details.addWidget(self.title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(6)
        details.addLayout(grid)

        self.lbl_email = QLabel("Email:")
        self.val_email = QLabel("—")
        self.val_email.setTextInteractionFlags(Qt.TextSelectableByMouse)
        grid.addWidget(self.lbl_email, 0, 0, Qt.AlignRight | Qt.AlignTop)
        grid.addWidget(self.val_email, 0, 1)

        self.lbl_username = QLabel("Username:")
        self.val_username = QLabel("—")
        self.val_username.setTextInteractionFlags(Qt.TextSelectableByMouse)
        grid.addWidget(self.lbl_username, 1, 0, Qt.AlignRight | Qt.AlignTop)
        grid.addWidget(self.val_username, 1, 1)

        self.lbl_link = QLabel("Site Link:")
        self.val_link = QLabel("—")
        self.val_link.setTextInteractionFlags(Qt.TextSelectableByMouse)
        grid.addWidget(self.lbl_link, 0, 2, Qt.AlignRight | Qt.AlignTop)
        grid.addWidget(self.val_link, 0, 3)

        self.lbl_totp = QLabel("TOTP:")

        totp_row = QHBoxLayout()
        totp_row.setContentsMargins(0, 0, 0, 0)
        totp_row.setSpacing(6)

        self.totp_ring = TotpRingWidget(self, period=30)
        self.totp_ring.setFixedSize(18, 18)

        self.totp_now = QLabel("—")
        self.totp_now.setToolTip("Current TOTP code · seconds remaining")
        self.totp_now.setWordWrap(False)

        totp_row.addWidget(self.totp_ring, 0, Qt.AlignLeft | Qt.AlignVCenter)
        totp_row.addWidget(self.totp_now, 0, Qt.AlignLeft | Qt.AlignVCenter)

        self.totp_wrap = QWidget(self)
        self.totp_wrap.setLayout(totp_row)

        grid.addWidget(self.lbl_totp, 1, 2, Qt.AlignRight | Qt.AlignTop)
        grid.addWidget(self.totp_wrap, 1, 3, Qt.AlignLeft  | Qt.AlignVCenter)

        self.lbl_totp.hide()
        self.totp_wrap.hide()

        self.notes = QPlainTextEdit()
        self.notes.setReadOnly(True)
        self.notes.setPlaceholderText("Notes")
        self.notes.setMinimumHeight(72)
        self.notes.setAttribute(Qt.WA_StyledBackground, True)
        self.notes.setViewportMargins(2, 2, 2, 2)
        details.addWidget(self.notes)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._otp_secret = ""

    def _show_empty(self, show: bool):
        self.empty_msg.setVisible(show)
        self.details_wrap.setVisible(not show)

    def start(self):
        if self.details_wrap.isVisible():
            if not self._timer.isActive():
                self._timer.start(1000)
            self.totp_ring.start(200)
            self._tick()

    def stop(self):
        try:
            if self._timer.isActive():
                self._timer.stop()
        except Exception:
            pass
        self.totp_ring.stop()

    def update_plain(self, plain: dict | None):
        if not plain:
            self._show_empty(True)
            self.title.setText("—")
            self.title.setToolTip("")
            self.val_email.setText("—")
            self.val_email.setToolTip("")
            self.val_username.setText("—")
            self.val_username.setToolTip("")
            self.val_link.setText("—")
            self.val_link.setToolTip("")
            self.notes.setPlainText("")
            self.notes.setToolTip("")
            self._set_totp(None)
            return

        self._show_empty(False)

        site_disp, site_tip = _limit_text(plain.get("site"), "site")
        self.title.setText(site_disp)
        self.title.setToolTip(site_tip if site_disp != "—" else "")

        email_disp, email_tip = _limit_text(plain.get("email"), "email")
        self.val_email.setText(email_disp)
        self.val_email.setToolTip(email_tip if email_disp != "—" else "")

        user_disp, user_tip = _limit_text(plain.get("username"), "username")
        self.val_username.setText(user_disp)
        self.val_username.setToolTip(user_tip if user_disp != "—" else "")

        link_disp, link_tip = _limit_text(plain.get("site_link"), "site_link")
        self.val_link.setText(link_disp)
        self.val_link.setToolTip(link_tip if link_disp != "—" else "")

        notes_full = plain.get("notes") or ""
        notes_disp, notes_tip = _limit_text(notes_full, "notes")
        self.notes.setPlainText("" if notes_disp == "—" else notes_disp)
        self.notes.setToolTip(notes_tip if notes_disp else "")

        self._set_totp(plain.get("otp_secret") or "")

    def _set_totp(self, secret: str | None):
        self._otp_secret = (secret or "").strip()
        has_secret = bool(self._otp_secret)

        self.lbl_totp.setVisible(has_secret)
        self.totp_wrap.setVisible(has_secret)

        self._tick()

    def _tick(self):
        if not self.details_wrap.isVisible():
            return

        secret = self._otp_secret
        if not secret:
            self.totp_now.setText("")
            self.totp_now.setToolTip("")
            self.totp_ring.set_remaining(0, period=30)
            return

        code, rem, period = totp_util.totp_from_uri_or_secret(secret)
        if not code:
            self.totp_now.setText("invalid secret")
            self.totp_now.setToolTip("invalid secret")
            self.totp_ring.set_remaining(0, period=period or 30)
            return

        text = f"{code}  ·  {rem:02d}s"
        disp, tip = _limit_text(text, "totp")
        self.totp_now.setText(disp)
        self.totp_now.setToolTip(tip)
        self.totp_ring.set_remaining(rem, period=period or 30)


class PreviewMixin:
    def _init_preview_pane(self, splitter_right: QSplitter):
        self.settings: SettingsManager = getattr(self, "settings", SettingsManager())
        self.splitter_r: QSplitter = splitter_right

        self._preview_panel = _PreviewPanel(self)
        self._preview_panel.setMinimumHeight(0)
        self._preview_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self._preview_panel._show_empty(True)

        if self.splitter_r.count() == 0:
            self.splitter_r.addWidget(QWidget())
        self.splitter_r.addWidget(self._preview_panel)

        self._restore_preview_size_later()

        try:
            self.table.itemSelectionChanged.connect(self.update_preview_for_selection)
        except Exception:
            pass

        self._preview_first_refresh_done = False
        
        QTimer.singleShot(250, self._first_refresh_after_login)

    def _first_refresh_after_login(self, _retries: int = 0):
        if getattr(self, "_preview_first_refresh_done", False):
            return

        if not getattr(self, "cipher", None):
            if _retries < 30:
                QTimer.singleShot(100, lambda: self._first_refresh_after_login(_retries + 1))
            return

        if not getattr(self, "table", None):
            if _retries < 30:
                QTimer.singleShot(100, lambda: self._first_refresh_after_login(_retries + 1))
            return

        try:
            sel = self.table.selectionModel().selectedRows()
            if sel:
                self._preview_first_refresh_done = True
                
                self._force_preview_update()
                return
            elif _retries < 30:
                QTimer.singleShot(100, lambda: self._first_refresh_after_login(_retries + 1))
        except Exception:
            if _retries < 30:
                QTimer.singleShot(100, lambda: self._first_refresh_after_login(_retries + 1))

    def _force_preview_update(self):
        try:
            selected = self.table.selectionModel().selectedRows()
            count = len(selected)
        except Exception:
            count = 0

        if count != 1:
            self._preview_panel.update_plain(None)
            return

        try:
            entry_id = self._get_selected_entry_id_from_table()
        except Exception:
            entry_id = None

        if not entry_id:
            self._preview_panel.update_plain(None)
            return

        row = db.fetch_entry_dict(int(entry_id))
        if not row:
            self._preview_panel.update_plain(None)
            return

        try:
            if dbx and self.cipher:
                plain = dbx.decrypt_row_to_plain(row, self.cipher)
            else:
                plain = db.decrypt_row_to_plain(row, self.cipher) \
                        if hasattr(db, "decrypt_row_to_plain") else dict(row)
        except Exception:
            plain = dict(row)

        self._set_preview_collapsed(False)
        self._preview_panel.update_plain(plain)
        self._preview_panel.start()

    def _restore_preview_size_later(self):
        def apply():
            try:
                collapsed = bool(self.settings.get("preview_collapsed", False))
                saved_h = int(self.settings.get("preview_height", 180) or 180)
            except Exception:
                collapsed = False
                saved_h = 180

            sizes = self.splitter_r.sizes()
            if len(sizes) != 2:
                return

            total = max(1, sum(sizes))
            ph = 0 if collapsed else max(80, saved_h)
            th = max(1, total - ph)
            self.splitter_r.setSizes([th, ph])

            if collapsed:
                self._preview_panel.stop()
            else:
                self._preview_panel.start()

            try:
                self.splitter_r.splitterMoved.connect(
                    self._on_splitter_moved,
                    Qt.ConnectionType.UniqueConnection
                )
            except TypeError:
                pass

        QTimer.singleShot(0, apply)

    def _on_splitter_moved(self, _pos: int, _index: int):
        sizes = self.splitter_r.sizes()
        if len(sizes) != 2:
            return
        preview_h = sizes[1]
        collapsed = preview_h < 8
        self.settings.set("preview_collapsed", collapsed)
        if collapsed:
            self._preview_panel.stop()
        else:
            self._preview_panel.start()
            self.settings.set("preview_height", preview_h)

    def update_preview_for_selection(self):
        if not getattr(self, "_preview_first_refresh_done", False):
            if not getattr(self, "cipher", None):
                return

        if not getattr(self, "cipher", None):
            QTimer.singleShot(50, self.update_preview_for_selection)
            return

        try:
            selected = self.table.selectionModel().selectedRows()
            count = len(selected)
        except Exception:
            count = 0

        if count > 1:
            self._set_preview_collapsed(True)
            self._preview_panel.update_plain(None)
            return

        if count == 0:
            self._preview_panel.update_plain(None)
            return

        try:
            entry_id = self._get_selected_entry_id_from_table()
        except Exception:
            entry_id = None

        if not entry_id:
            self._preview_panel.update_plain(None)
            return

        row = db.fetch_entry_dict(int(entry_id))
        if not row:
            self._preview_panel.update_plain(None)
            return

        try:
            if dbx and getattr(self, "cipher", None):
                plain = dbx.decrypt_row_to_plain(row, self.cipher)
            else:
                plain = db.decrypt_row_to_plain(row, getattr(self, "cipher", None)) \
                        if hasattr(db, "decrypt_row_to_plain") else dict(row)
        except Exception:
            plain = dict(row)

        self._set_preview_collapsed(False)
        self._preview_panel.update_plain(plain)
        self._preview_panel.start()

    def _set_preview_collapsed(self, collapsed: bool):
        sizes = self.splitter_r.sizes()
        if len(sizes) != 2:
            return
        total = max(1, sum(sizes))
        try:
            saved_h = int(self.settings.get("preview_height", 180) or 180)
        except Exception:
            saved_h = 180

        ph = 0 if collapsed else max(80, saved_h)
        th = max(1, total - ph)
        self.splitter_r.setSizes([th, ph])
        self.settings.set("preview_collapsed", bool(collapsed))
        if collapsed:
            self._preview_panel.stop()
        else:
            self._preview_panel.start()
            self.settings.set("preview_height", ph)

    def _stop_preview_timers(self):
        try:
            self._preview_panel.stop()
        except Exception:
            pass