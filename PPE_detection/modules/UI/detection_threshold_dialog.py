from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDialogButtonBox,
    QGroupBox, QGridLayout, QSlider, QHBoxLayout, QWidget,
)
from PyQt5.QtCore import Qt


class DetectionThresholdsDialog(QDialog):
    def __init__(self, camera_index, current_thresholds, camera_source, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.camera_source = camera_source
        self.current_thresholds = current_thresholds
        self.setWindowTitle(f"Настройка порогов детекции - Камера {camera_source}")
        self.setModal(True)
        self.resize(500, 450)
        self._init_ui()
        self._load_current_thresholds()

    def _create_slider_with_value(self, label_text, default_value=0.5):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(label_text)
        label.setMinimumWidth(100)
        layout.addWidget(label)


        slider = QSlider(Qt.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(default_value * 100))
        slider.setTickPosition(QSlider.TicksBelow)
        slider.setTickInterval(10)
        layout.addWidget(slider)

        value_label = QLabel(f"{default_value:.2f}")
        value_label.setMinimumWidth(40)
        value_label.setAlignment(Qt.AlignRight)
        layout.addWidget(value_label)

        slider.value_label = value_label
        slider.valueChanged.connect(lambda v: self._on_slider_changed(v, value_label))

        return container, slider

    def _on_slider_changed(self, value, label):
        actual_value = value / 100.0
        label.setText(f"{actual_value:.2f}")

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        header = QLabel(f"Адрес: {self.camera_source}")
        header.setStyleSheet("font-weight: bold; font-size: 12pt; margin-bottom: 10px;")
        layout.addWidget(header)

        group = QGroupBox("Пороги уверенности детекции")
        grid = QGridLayout(group)
        grid.setVerticalSpacing(12)
        grid.setHorizontalSpacing(10)

        self.head_container, self.head_slider = self._create_slider_with_value("Голова (head):", 0.6)
        grid.addWidget(self.head_container, 0, 0, 1, 2)

        self.helmet_container, self.helmet_slider = self._create_slider_with_value("Каска (helmet):", 0.5)
        grid.addWidget(self.helmet_container, 1, 0, 1, 2)

        self.body_container, self.body_slider = self._create_slider_with_value("Тело (body):", 0.6)
        grid.addWidget(self.body_container, 2, 0, 1, 2)

        self.vest_container, self.vest_slider = self._create_slider_with_value("Жилет (vest):", 0.5)
        grid.addWidget(self.vest_container, 3, 0, 1, 2)

        self.palm_container, self.palm_slider = self._create_slider_with_value("Ладонь (palm):", 0.4)
        grid.addWidget(self.palm_container, 4, 0, 1, 2)

        self.glove_container, self.glove_slider = self._create_slider_with_value("Перчатка (glove):", 0.3)
        grid.addWidget(self.glove_container, 5, 0, 1, 2)

        self.person_container, self.person_slider = self._create_slider_with_value("Человек (person):", 0.7)
        grid.addWidget(self.person_container, 6, 0, 1, 2)

        layout.addWidget(group)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _load_current_thresholds(self):
        self.head_slider.setValue(int(self.current_thresholds.get('head', 0.6) * 100))
        self.helmet_slider.setValue(int(self.current_thresholds.get('helmet', 0.5) * 100))
        self.body_slider.setValue(int(self.current_thresholds.get('body', 0.6) * 100))
        self.vest_slider.setValue(int(self.current_thresholds.get('vest', 0.5) * 100))
        self.palm_slider.setValue(int(self.current_thresholds.get('palm', 0.4) * 100))
        self.glove_slider.setValue(int(self.current_thresholds.get('glove', 0.3) * 100))
        self.person_slider.setValue(int(self.current_thresholds.get('person', 0.7) * 100))

    def get_thresholds(self):
        return {
            'head': round(self.head_slider.value() / 100.0, 2),
            'helmet': round(self.helmet_slider.value() / 100.0, 2),
            'body': round(self.body_slider.value() / 100.0, 2),
            'vest': round(self.vest_slider.value() / 100.0, 2),
            'palm': round(self.palm_slider.value() / 100.0, 2),
            'glove': round(self.glove_slider.value() / 100.0, 2),
            'person': round(self.person_slider.value() / 100.0, 2)
        }
