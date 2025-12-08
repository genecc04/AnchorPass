import secrets
from pathlib import Path
from PySide6.QtWidgets import ( QWidget, QVBoxLayout, QFormLayout, QSpinBox, QLineEdit, QCheckBox, QLabel, 
QComboBox, QPushButton, QHBoxLayout, QFileDialog )


class PassphraseTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._words = []
        self._wordlist_path = ""

        layout = QVBoxLayout(self)

        self.pp_words = QSpinBox()
        self.pp_words.setRange(2, 12)
        self.pp_words.setValue(4)

        self.pp_separator = QLineEdit()
        self.pp_separator.setPlaceholderText("e.g., -  _  space")
        self.pp_separator.setText("-")

        self.pp_case = QComboBox()
        self.pp_case.addItems([
            "Capitalize words",
            "Lower case words",
            "Upper case words",
            "Mixed case words",
        ])
        self.pp_case.setCurrentIndex(0)

        self.pp_append_number = QCheckBox("Append random number (0–9)")
        self.pp_append_symbol = QCheckBox("Append random symbol (!@#$%^&*)")

        self.wordlist_path_edit = QLineEdit()
        self.wordlist_path_edit.setReadOnly(True)
        self.wordlist_path_edit.setPlaceholderText("No word list selected")

        self.wordlist_browse_btn = QPushButton("Browse…")
        self.wordlist_browse_btn.clicked.connect(self._browse_wordlist)

        picker_row = QHBoxLayout()
        picker_row.addWidget(self.wordlist_path_edit, 1)
        picker_row.addWidget(self.wordlist_browse_btn, 0)

        self.word_count_label = QLabel("Words loaded: 0")

        form = QFormLayout()
        form.addRow("Number of words:", self.pp_words)
        form.addRow("Separator:", self.pp_separator)
        form.addRow("Case:", self.pp_case)
        form.addRow("", self.pp_append_number)
        form.addRow("", self.pp_append_symbol)
        form.addRow("Word list file:", QWidget())

        layout.addLayout(form)
        layout.addLayout(picker_row)
        layout.addWidget(self.word_count_label)
        layout.addStretch(1)

        self._try_load_default_wordlist()

    def _try_load_default_wordlist(self):
        try:
            tabs_dir = Path(__file__).resolve().parent
            pkg_dir = tabs_dir.parent
            project_root = pkg_dir.parent
            default_path = project_root / "assets" / "wordlist" / "wordlist.txt"
            if default_path.is_file():
                self._load_wordlist_from_path(default_path)
        except Exception:
            pass

    def _load_wordlist_from_path(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                words = []
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or s.startswith(";"):
                        continue

                    parts = s.split()
                    if not parts:
                        continue
                    words.append(parts[-1])
        except Exception as e:
            self._words = []
            self._wordlist_path = ""
            self.wordlist_path_edit.setText("")
            self.word_count_label.setText(f"Failed to load list: {e}")
            return

        self._words = words
        self._wordlist_path = str(path)
        self.wordlist_path_edit.setText(self._wordlist_path)
        self.word_count_label.setText(f"Words loaded: {len(self._words)}")

    def _browse_wordlist(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select word list (one word per line or Diceware format)",
            "",
            "Text files (*.txt);;All files (*.*)"
        )
        if not path_str:
            return
        self._load_wordlist_from_path(Path(path_str))

    def _apply_case(self, words):
        mode = self.pp_case.currentText()
        if mode == "Capitalize words":
            return [w.capitalize() for w in words]
        if mode == "Lower case words":
            return [w.lower() for w in words]
        if mode == "Upper case words":
            return [w.upper() for w in words]
        if mode == "Mixed case words":
            mixed = []
            for w in words:
                chars = [(ch.upper() if secrets.choice([True, False]) else ch.lower()) for ch in w]
                mixed.append("".join(chars))
            return mixed
        return words

    def generate_passphrase(self) -> str:
        if not self._words:
            raise ValueError(
                "No word list loaded. Either place one at assets/wordlist/wordlist.txt "
                "or click 'Browse…' to select a file with one word per line or Diceware format."
            )

        count = self.pp_words.value()
        sep = self.pp_separator.text()

        chosen = [secrets.choice(self._words) for _ in range(count)]
        chosen = self._apply_case(chosen)

        phrase = sep.join(chosen)

        if self.pp_append_number.isChecked():
            phrase += secrets.choice("0123456789")
        if self.pp_append_symbol.isChecked():
            phrase += secrets.choice("!@#$%^&*")

        return phrase
