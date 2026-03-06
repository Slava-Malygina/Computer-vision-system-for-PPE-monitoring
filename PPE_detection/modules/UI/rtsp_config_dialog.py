from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QLineEdit, QDialogButtonBox,
    QGroupBox, QGridLayout, QToolButton
)


class RtspConfigDialog(QDialog):
    MAX_SOURCES = 4

    def __init__(self, parent=None, existing_addresses=None, validator_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка IP-камер")
        self.setModal(True)
        self.resize(520, 280)

        self.rtsp_inputs = []
        self.remove_buttons = []
        self.validator_callback = validator_callback

        self._init_ui(existing_addresses or [""] * self.MAX_SOURCES)

    def _init_ui(self, existing_addresses):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        header = QLabel("Настройка камер")
        header.setStyleSheet("font-weight: bold; font-size: 13pt; margin-bottom: 5px;")
        main_layout.addWidget(header)

        group = QGroupBox()
        grid = QGridLayout(group)
        grid.setVerticalSpacing(10)

        for i in range(self.MAX_SOURCES):
            label = QLabel(f"Камера {i + 1}:")
            label.setMinimumWidth(70)

            line_edit = QLineEdit()
            line_edit.setPlaceholderText("rtsp://")
            line_edit.setClearButtonEnabled(True)
            line_edit.setText(existing_addresses[i] if i < len(existing_addresses) else "")
            line_edit.textChanged.connect(lambda _, idx=i: self._on_text_changed(idx))


            remove_btn = QToolButton()
            remove_btn.setText("✕")
            remove_btn.setFixedSize(26, 26)
            remove_btn.setToolTip("Удалить адрес")
            remove_btn.setStyleSheet("""
                QToolButton {
                    background-color: #e74c3c;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QToolButton:hover { background-color: #c0392b; }
                QToolButton:disabled { background-color: #555; }
            """)
            remove_btn.setEnabled(bool(existing_addresses[i].strip()))
            remove_btn.clicked.connect(lambda _, idx=i: self._remove_address(idx))

            self.rtsp_inputs.append(line_edit)
            self.remove_buttons.append(remove_btn)
            grid.addWidget(label, i, 0)
            grid.addWidget(remove_btn, i, 2)
            grid.addWidget(line_edit, i, 1)

        main_layout.addWidget(group)
        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        main_layout.addWidget(btn_box)

    def _on_text_changed(self, index):
        """Визуальная валидация при вводе."""
        edit = self.rtsp_inputs[index]
        text = edit.text().strip()

        if self.validator_callback:
            is_valid = self.validator_callback(text)
        else:
            is_valid = text == "" or text.lower().startswith(("rtsp://", "rtsps://", "rtmp://"))

        edit.setStyleSheet("" if is_valid else "border: 1px solid #e74c3c; border-radius: 3px;")
        self.remove_buttons[index].setEnabled(bool(text))

    def get_addresses(self):
        return [edit.text().strip() for edit in self.rtsp_inputs]

    @staticmethod
    def open_and_get(parent, existing=None, validator=None):
        dialog = RtspConfigDialog(parent, existing, validator)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_addresses()
        return None

    def _remove_address(self, index):
        self.rtsp_inputs[index].clear()
        self._on_text_changed(index)