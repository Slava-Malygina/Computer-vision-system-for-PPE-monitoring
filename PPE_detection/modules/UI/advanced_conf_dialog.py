from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QDialogButtonBox


class AdvancedConfDialog(QDialog):
    def __init__(self, parent=None, current_thresholds=None):
        super().__init__(parent)
        self.setWindowTitle("Пороги уверенности по классам")
        self.setModal(True)
        self.resize(400, 300)

        default_thresholds = {
            'helmet': 0.4,
            'vest': 0.5,
            'glove': 0.3,
            'head': 0.7,
            'body': 0.6,
            'palm': 0.4,
        }

        self.thresholds = current_thresholds or default_thresholds
        self.sliders = {}

        layout = QVBoxLayout()

        for cls_name, conf in self.thresholds.items():
            row = QHBoxLayout()
            label = QLabel(f"{cls_name.capitalize()}:")
            label.setMinimumWidth(80)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(10, 100)
            slider.setValue(int(conf * 100))
            value_label = QLabel(f"{conf:.2f}")
            value_label.setMinimumWidth(40)

            slider.valueChanged.connect(
                lambda val, lbl=value_label: lbl.setText(f"{val / 100:.2f}")
            )

            row.addWidget(label)
            row.addWidget(slider)
            row.addWidget(value_label)

            self.sliders[cls_name] = (slider, value_label)
            layout.addLayout(row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def get_thresholds(self):
        return {
            cls: self.sliders[cls][0].value() / 100.0
            for cls in self.sliders
        }