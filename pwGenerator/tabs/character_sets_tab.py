import string
from PySide6.QtWidgets import ( QWidget, QVBoxLayout, QGroupBox, QGridLayout, QCheckBox, QLineEdit, QFormLayout )

class CharacterSetsTab(QWidget):

    EXCLUDED_SIMILAR = set("O0l1I|")

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.use_lower     = QCheckBox("Lowercase (a–z)"); self.use_lower.setChecked(True)
        self.use_upper     = QCheckBox("Uppercase (A–Z)"); self.use_upper.setChecked(True)
        self.use_digits    = QCheckBox("Digits (0–9)");    self.use_digits.setChecked(True)
        self.use_symbols   = QCheckBox("Symbols (!@#$…)"); self.use_symbols.setToolTip("!@#$%^&*")
        self.use_punct     = QCheckBox("Punctuation (.,;:!?)"); self.use_punct.setToolTip(".,;:!?")
        self.use_quotes    = QCheckBox("Quotes (' \" `)"); self.use_quotes.setToolTip("' \" `")
        self.use_dashslash = QCheckBox("Dashes & Slashes (- _ / \\)"); self.use_dashslash.setToolTip("- _ / \\")
        self.use_math      = QCheckBox("Math symbols (+ = * % < > ^ ~ |)"); self.use_math.setToolTip("+=*%<>^~|")
        self.use_braces    = QCheckBox("Braces (() [] {})"); self.use_braces.setToolTip("() [] {}")

        sets_group = QGroupBox("Character Sets")
        sets_grid = QGridLayout()
        checks = [
            self.use_lower, self.use_upper, self.use_digits,
            self.use_symbols, self.use_punct, self.use_quotes,
            self.use_dashslash, self.use_math, self.use_braces,
        ]
        for idx, cb in enumerate(checks):
            r, c = divmod(idx, 3)
            sets_grid.addWidget(cb, r, c)
        sets_group.setLayout(sets_grid)

        self.custom_include = QLineEdit()
        self.custom_include.setPlaceholderText("e.g., @€# or any characters to include")

        self.custom_exclude = QLineEdit()
        self.custom_exclude.setPlaceholderText("e.g., O0l1I| (characters to exclude)")

        form = QFormLayout()
        form.addRow("Also choose from:", self.custom_include)
        form.addRow("Do not include:", self.custom_exclude)

        self.exclude_similar = QCheckBox("Exclude similar (O/0, l/1, I/|)")
        self.exclude_similar.setChecked(True)
        self.ensure_each = QCheckBox("Ensure one from each selected set")
        self.ensure_each.setChecked(True)

        layout.addWidget(sets_group)
        layout.addLayout(form)
        layout.addWidget(self.exclude_similar)
        layout.addWidget(self.ensure_each)
        layout.addStretch(1)

    def ensure_each_checked(self) -> bool:
        return self.ensure_each.isChecked()

    def _filter_similar(self, s: str) -> str:
        if not self.exclude_similar.isChecked():
            return s
        return "".join(ch for ch in s if ch not in self.EXCLUDED_SIMILAR)

    def _apply_blacklist(self, s: str) -> str:
        blacklist = set(self.custom_exclude.text())
        if not blacklist:
            return s
        return "".join(ch for ch in s if ch not in blacklist)

    def selected_pools(self):
        raw = []
        if self.use_lower.isChecked():     raw.append(string.ascii_lowercase)
        if self.use_upper.isChecked():     raw.append(string.ascii_uppercase)
        if self.use_digits.isChecked():    raw.append(string.digits)
        if self.use_symbols.isChecked():   raw.append("!@#$%^&*")
        if self.use_punct.isChecked():     raw.append(".,;:!?")
        if self.use_quotes.isChecked():    raw.append("'\"`")
        if self.use_dashslash.isChecked(): raw.append("-_/\\")
        if self.use_math.isChecked():      raw.append("+=*%<>^~|")
        if self.use_braces.isChecked():    raw.append("()[]{}")

        include_raw = self.custom_include.text()
        if include_raw:
            raw.append(include_raw)

        if not raw:
            return []

        pools = [self._apply_blacklist(self._filter_similar(p)) for p in raw]
        pools = [p for p in pools if p]
        return pools
