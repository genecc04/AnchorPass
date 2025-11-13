import secrets
from collections import OrderedDict
from typing import Callable, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import ( QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFormLayout, QWidget, 
                               QTabWidget, QComboBox, QMessageBox)

from ui.widgets.plusminus_spinbox import PlusMinusSpinBox

from pwGenerator.tabs.character_sets_tab import CharacterSetsTab
from pwGenerator.tabs.passphrase_tab import PassphraseTab

try:
    from core.settings_manager import SettingsManager
except Exception:
    SettingsManager = None

from ui.widgets.password_field import PasswordLineEdit


class PasswordGeneratorDialog(QDialog):

    def __init__( self, parent=None, *, targets: Optional[Dict[str, Callable[[str], None]]] = None, 
                 initial_target: Optional[str] = None, icon_family: str | None = None, ):
        super().__init__(parent)
        self.setWindowTitle("Password Generator")
        self.setModal(True)
        self.setMinimumWidth(720)
        self.adjustSize()
        self.setSizeGripEnabled(False)
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(Qt.MSWindowsFixedSizeDialogHint, True)

        self.length = PlusMinusSpinBox()
        self.length.setRange(4, 128)
        self.length.setValue(16)

        self._targets = self._build_targets(targets)

        self.target_combo = QComboBox()
        for label in self._targets.keys():
            self.target_combo.addItem(label)

        self._both_label = None
        real_labels = [k for k in self._targets.keys() if k != "Output only"]
        if len(real_labels) == 2:
            self._both_label = "Both"
            self.target_combo.addItem(self._both_label)

        self._select_initial(initial_target)

        left_form = QFormLayout()
        left_form.addRow("Length:", self.length)
        left_form.addRow("Selected:", self.target_combo)

        self.tabs = QTabWidget()
        self.charsets_tab = CharacterSetsTab()
        self.passphrase_tab = PassphraseTab()
        self.tabs.addTab(self.charsets_tab, "Character Sets")
        self.tabs.addTab(self.passphrase_tab, "Pass phrase")

        top = QHBoxLayout()
        top.addLayout(left_form, 1)
        right_col = QVBoxLayout()
        right_col.addWidget(self.tabs)
        top.addLayout(right_col, 2)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(QLabel("Password:"))

        clear_ms = 10_000
        if SettingsManager is not None:
            try:
                clear_ms = max(0, int(SettingsManager().get("clipboard_clear_seconds", 15))) * 1000
            except Exception:
                pass

        self.output = PasswordLineEdit(
            placeholder="Type or click Generate…",
            clear_clipboard_after_ms=clear_ms,
            icon_point_size=18,
            icon_padding=2,
            strength_alpha=0.12,
            strength_enabled=True,
            icon_family=icon_family,
            copy_enabled=True,
            parent=self,
        )

        out_block = QWidget()
        out_v = QVBoxLayout(out_block)
        out_v.setContentsMargins(0, 0, 0, 0)
        out_v.setSpacing(2)
        out_v.addWidget(self.output)

        root.addWidget(out_block)

        self.btn_generate = QPushButton("Generate")
        self.btn_apply = QPushButton("Apply")
        self.btn_close = QPushButton("Close")

        actions = QHBoxLayout()
        actions.addWidget(self.btn_generate)
        actions.addWidget(self.btn_apply)
        actions.addStretch(1)
        actions.addWidget(self.btn_close)
        root.addLayout(actions)

        self.btn_generate.clicked.connect(self.generate_password)
        self.btn_apply.clicked.connect(self.apply_to_targets)
        self.btn_close.clicked.connect(self.accept)

        self.output.textChanged.connect(self._on_output_changed)

    def _build_targets(self, incoming: Optional[Dict[str, Callable[[str], None]]]) -> "OrderedDict[str, Callable[[str], None]]":
        od = OrderedDict()
        if incoming:
            for label, setter in incoming.items():
                if callable(setter):
                    od[label] = setter
            if od:
                return od

        p = self.parent()
        added_any = False
        if p is not None and hasattr(p, "password") and hasattr(p.password, "setText"):
            od["Password"] = p.password.setText
            added_any = True
        if p is not None and hasattr(p, "app_password") and hasattr(p.app_password, "setText"):
            od["App Password"] = p.app_password.setText
            added_any = True

        if not added_any:
            od["Output only"] = lambda text: None

        return od

    def _select_initial(self, initial_label: Optional[str]):
        if initial_label:
            idx = self.target_combo.findText(
                initial_label,
                Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive
            )
            if idx == -1:
                idx = self.target_combo.findText(initial_label, Qt.MatchFlag.MatchContains)
            if idx != -1:
                self.target_combo.setCurrentIndex(idx)
                return

        idx = self.target_combo.findText("Password")
        if idx != -1:
            self.target_combo.setCurrentIndex(idx)
            return
        idx = self.target_combo.findText("App Password")
        if idx != -1:
            self.target_combo.setCurrentIndex(idx)
            return

    def selected_label(self) -> str:
        return self.target_combo.currentText()

    def _on_output_changed(self, _):
        pass

    def _generate_from_charsets(self) -> str:
        pools = self.charsets_tab.selected_pools()
        if not pools:
            raise ValueError("Please select or enter at least one usable character set.")

        length = self.length.value()
        ensure_each = self.charsets_tab.ensure_each_checked()

        if ensure_each:
            if length < len(pools):
                raise ValueError(f"Length must be ≥ number of selected sets ({len(pools)}).")
            password_chars = [secrets.choice(pool) for pool in pools]
            all_chars = "".join(pools)
            remaining = length - len(password_chars)
            password_chars += [secrets.choice(all_chars) for _ in range(remaining)]
        else:
            all_chars = "".join(pools)
            if not all_chars:
                raise ValueError("Character sets are empty after filtering.")
            password_chars = [secrets.choice(all_chars) for _ in range(length)]

        for i in range(len(password_chars) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            password_chars[i], password_chars[j] = password_chars[j], password_chars[i]
        return "".join(password_chars)

    def generate_password(self):
        try:
            if self.tabs.currentIndex() == 0:
                pwd = self._generate_from_charsets()
            else:
                pwd = self.passphrase_tab.generate_passphrase()
        except ValueError as e:
            QMessageBox.warning(self, "Cannot generate", str(e))
            return

        self.output.setText(pwd)

    def apply_to_targets(self):
        text = self.output.text()
        if not text:
            return

        label = self.selected_label()

        if self._both_label and label == self._both_label:
            for k, setter in self._targets.items():
                if k != "Output only":
                    try:
                        setter(text)
                    except Exception:
                        pass
        else:
            setter = self._targets.get(label)
            if setter:
                try:
                    setter(text)
                except Exception:
                    pass

        self.accept()
