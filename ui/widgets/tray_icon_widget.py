from PySide6.QtWidgets import QSystemTrayIcon, QApplication, QMessageBox
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject, Slot
from ui.widgets.rounded_menu import RoundedMenu


class TrayIconWidget(QObject):
    def __init__(self, parent, on_open, on_lock_db, icon: QIcon | None = None, tooltip: str = "My App"):
        super().__init__(parent)

        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(parent, "Tray", "System tray is not available on this system.")
            return

        self._on_open = on_open
        self._on_lock_db = on_lock_db

        self.tray = QSystemTrayIcon(parent)

        if icon is None or icon.isNull():
            icon = parent.windowIcon()
        self.tray.setIcon(icon)

        self.tray.setToolTip(tooltip)
        self._create_menu()
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _create_menu(self):
        menu = RoundedMenu(self.parent())

        self.action_open = QAction("Open", self)
        self.action_lock = QAction("Lock Database", self)
        self.action_exit = QAction("Exit", self)

        self.action_open.triggered.connect(self._handle_open)
        self.action_lock.triggered.connect(self._handle_lock)
        self.action_exit.triggered.connect(self._handle_exit)

        menu.addAction(self.action_open)
        menu.addAction(self.action_lock)
        menu.addSeparator()
        menu.addAction(self.action_exit)

        self.tray.setContextMenu(menu)

    @Slot()
    def _handle_open(self):
        if callable(self._on_open):
            self._on_open()

    @Slot()
    def _handle_lock(self):
        if callable(self._on_lock_db):
            self._on_lock_db()

    @Slot()
    @Slot()
    def _handle_exit(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "maybe_auto_backup"):
            try:
                parent.maybe_auto_backup("close")
            except Exception:
                pass

        app = QApplication.instance()
        if app is not None:
            app.quit()

    @Slot(QSystemTrayIcon.ActivationReason)
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._handle_open()

    def show(self):
        self.tray.show()

    def hide(self):
        self.tray.hide()

    def is_visible(self) -> bool:
        return self.tray.isVisible()

    def set_icon(self, icon: QIcon):
        self.tray.setIcon(icon)

    def set_tooltip(self, text: str):
        self.tray.setToolTip(text)
