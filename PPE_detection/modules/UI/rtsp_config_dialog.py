import os

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QLineEdit, QDialogButtonBox,
    QGroupBox, QGridLayout, QToolButton, QMessageBox, QHBoxLayout, QPushButton
)

from modules.UI.detection_threshold_dialog import DetectionThresholdsDialog
from modules.utils.threshold_manager import ThresholdManager

DEFAULT_THRESHOLDS = {
    'head': 0.6,
    'helmet': 0.5,
    'body': 0.6,
    'vest': 0.5,
    'palm': 0.4,
    'glove': 0.3,
    'person': 0.7
}
class RtspConfigDialog(QDialog):
    MAX_SOURCES = 4
    SESSION_SAVED = QDialog.DialogCode(2)
    def __init__(self, parent=None, existing_addresses=None, validator_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Настройка IP-камер")
        self.setModal(True)
        self.resize(520, 280)
        self.settings_buttons = []
        self.rtsp_inputs = []
        self.remove_buttons = []
        self.validator_callback = validator_callback
        self.threshold_manager = ThresholdManager()
        self.session_thresholds = {}
        self.session_addresses = None
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
            base_path = os.path.dirname(os.path.abspath(__file__))
            icon_path = os.path.normpath(os.path.join(base_path, "..", "icons", "ic_settings.png"))
            settings_btn = QToolButton()
            settings_btn.setIcon(QIcon(icon_path))
            settings_btn.setFixedSize(26, 26)
            settings_btn.setToolTip("Настройки камеры")
            settings_btn.setStyleSheet("""
                    QToolButton {
                        background-color: #3498db;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-weight: bold;
                    }
                    QToolButton:hover { background-color: #2980b9; }
                """)
            settings_btn.clicked.connect(lambda _, idx=i: self._on_settings_clicked(idx))


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
            self.settings_buttons.append(settings_btn)

            grid.addWidget(label, i, 0)
            grid.addWidget(line_edit, i, 1)
            grid.addWidget(remove_btn, i, 2)
            grid.addWidget(settings_btn, i, 3)

        main_layout.addWidget(group)

        btn_layout = QHBoxLayout()
        session_save_btn = QPushButton("Сохранить для сессии")
        session_save_btn.setToolTip("Сохранить настройки только для текущей сессии")
        session_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        session_save_btn.clicked.connect(self._save_session_settings)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        btn_layout.addWidget(session_save_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_box)

        main_layout.addLayout(btn_layout)

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
        result = dialog.exec_()
        if result == QDialog.Accepted:
            addresses = dialog.get_addresses()
            for address in addresses:
                if address and not dialog.threshold_manager.threshold_exists(address):
                    dialog.threshold_manager.set_thresholds(address, DEFAULT_THRESHOLDS)
            return addresses
        elif result == RtspConfigDialog.SESSION_SAVED:
            return dialog.session_addresses
        return None


    def _remove_address(self, index):
        self.rtsp_inputs[index].clear()
        self._on_text_changed(index)

    def _on_settings_clicked(self, index):
        current_address = self.rtsp_inputs[index].text().strip()
        if not current_address:
            QMessageBox.warning(self, "Предупреждение",
                                f"Сначала введите RTSP адрес для камеры {index + 1}")
            return

        if self.threshold_manager:
            current_thresholds = self.threshold_manager.get_thresholds(current_address)
        else:
            current_thresholds = DEFAULT_THRESHOLDS.copy()

        dialog = DetectionThresholdsDialog(
            camera_index=index,
            current_thresholds=current_thresholds,
            camera_source=current_address,
            parent=self
        )

        if dialog.exec_() == QDialog.Accepted:
            new_thresholds = dialog.get_thresholds()

            for key, value in new_thresholds.items():
                print(f"  - {key}: {value}")
            if self.threshold_manager:
                self.threshold_manager.set_thresholds(current_address, new_thresholds)


    def _save_session_settings(self):
        addresses = [edit.text().strip() for edit in self.rtsp_inputs if edit.text().strip()]
        self.session_addresses = addresses
        self.done(self.SESSION_SAVED)

    def get_session_addresses(self):
        return self.session_addresses
