from PyQt5.QtWidgets import (
     QVBoxLayout, QDateEdit, QTimeEdit, QPushButton, QGroupBox, QRadioButton,
    QSpinBox
)
from PyQt5.QtCore import QDate, QTime
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QSlider

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox


class FilterPanel(QWidget):
    downloadRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignTop)
        filter_group = QGroupBox("Фильтровать")
        filter_layout = QVBoxLayout()
        filter_layout.setContentsMargins(5, 5, 5, 5)

        filter_group.setLayout(filter_layout)
        type_layout = QHBoxLayout()

        camera_layout = QHBoxLayout()
        camera_label = QLabel("По камере:")
        self.camera_combo = CheckableComboBox()
        self.camera_combo.addItem("rtsp://localhost:8554/stream1", checked=True)
        self.camera_combo.addItem("rtsp://localhost:8554/stream2", checked=True)
        self.camera_combo.addItem("rtsp://localhost:8554/stream3", checked=True)
        self.camera_combo.addItem("rtsp://localhost:8554/stream4", checked=True)
        self.camera_combo.addItem("Веб-камера", checked=True)
        self.camera_combo.addItem("Видео", checked=True)

        camera_layout.addWidget(camera_label)
        camera_layout.addWidget(self.camera_combo)
        filter_layout.addLayout(camera_layout)


        type_label = QLabel("По нарушению:")
        self.type_combo = QComboBox()
        self.type_combo = CheckableComboBox()
        self.type_combo.addItem("Без каски", checked=True)
        self.type_combo.addItem("Без жилета", checked=True)
        self.type_combo.addItem("Без перчаток", checked=True)

        type_layout.addWidget(type_label)
        type_layout.addWidget(self.type_combo)
        filter_layout.addLayout(type_layout)

        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Дата с:"))
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1))
        self.date_from.setCalendarPopup(True)
        date_layout.addWidget(self.date_from)

        date_layout.addWidget(QLabel("по:"))
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        date_layout.addWidget(self.date_to)
        filter_layout.addLayout(date_layout)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("Время с:"))
        self.time_from = QTimeEdit(QTime(0, 0))
        time_layout.addWidget(self.time_from)

        time_layout.addWidget(QLabel("по:"))
        self.time_to = QTimeEdit(QTime(23, 59))
        time_layout.addWidget(self.time_to)
        filter_layout.addLayout(time_layout)
        self.prob_slider = RangeSlider(0, 100)
        prob_layout = QHBoxLayout()
        prob_layout.addWidget(self.prob_slider)
        filter_layout.addLayout(prob_layout)

        self.prob_slider.valueChanged.connect(lambda min_val, max_val: print(min_val, max_val))

        main_layout.addWidget(filter_group)
        main_layout.addSpacing(15)
        sort_group = QGroupBox("Сортировать")
        sort_layout = QHBoxLayout()
        sort_group.setLayout(sort_layout)

        self.sort_field = QComboBox()
        self.sort_field.addItems(["Дата", "Время", "ID нарушителя", "Тип нарушения", "Вероятность"])
        self.sort_order = QComboBox()
        self.sort_order.addItems(["По возрастанию", "По убыванию"])
        sort_layout.addWidget(self.sort_field)
        sort_layout.addWidget(self.sort_order)
        main_layout.addWidget(sort_group)
        main_layout.addSpacing(15)
        btn_layout = QHBoxLayout()
        self.apply_btn = QPushButton("Применить")
        self.reset_btn = QPushButton("Сбросить")
        btn_layout.addWidget(self.apply_btn)
        btn_layout.addWidget(self.reset_btn)
        main_layout.addLayout(btn_layout)
        main_layout.addSpacing(50)
        report_group = QGroupBox("Отчетность")
        report_layout = QVBoxLayout()
        report_group.setLayout(report_layout)

        report_type_layout = QHBoxLayout()
        self.full_report_radio = QRadioButton("Полный отчет")
        self.filtered_report_radio = QRadioButton("Отфильтрованный отчет")
        self.full_report_radio.setChecked(True)
        report_type_layout.addWidget(self.full_report_radio)
        report_type_layout.addWidget(self.filtered_report_radio)
        report_layout.addLayout(report_type_layout)

        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("Количество записей:"))
        self.record_count = QSpinBox()
        self.record_count.setRange(1, 100000)
        self.record_count.setValue(100)
        count_layout.addWidget(self.record_count)
        report_layout.addLayout(count_layout)

        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["CSV", "XLSX", "PDF"])
        format_layout.addWidget(self.format_combo)
        report_layout.addLayout(format_layout)

        self.download_btn = QPushButton("Скачать отчет")
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.download_btn)
        btn_layout.addStretch()
        report_layout.addLayout(btn_layout)

        main_layout.addWidget(report_group)
        self.download_btn.clicked.connect(self.downloadRequested.emit)
        self.setStyleSheet("""
            QDateEdit, QTimeEdit, QSpinBox {
                background-color: #2a2e35;
                color: #ffffff;
                border: 1px solid #3a424e;
                border-radius: 4px;
                padding: 2px 4px;
            }
             QTimeEdit::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #3a424e;
                background: transparent; 
            }
            QDateEdit::down-arrow, QDateEdit::up-arrow {
                width: 10px;
                height: 10px;
            }
              QPushButton {
                        background-color: #3a7fff;  
                        color: #ffffff;
                        border: 1px solid #2a68ff;
                        border-radius: 4px;
                        padding: 4px 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #5a8fff;
                    }
                    QPushButton:pressed {
                        background-color: #2a5fff;
                    }
            """)

    def get_filter_params(self):
        violations = []
        for i in range(self.type_combo.count()):
            item = self.type_combo.model().item(i)
            if item.checkState() == Qt.Checked:
                violations.append(item.text())

        cameras = []
        for i in range(self.camera_combo.count()):
            item = self.camera_combo.model().item(i)
            if item.checkState() == Qt.Checked:
                cameras.append(item.text())

        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()

        time_from = self.time_from.time().toPyTime()
        time_to = self.time_to.time().toPyTime()
        prob_min = self.prob_slider.min_value / 100.0
        prob_max = self.prob_slider.max_value / 100.0
        sort_field = self.sort_field.currentText()
        sort_order = self.sort_order.currentText()

        return {
            "violations": violations,
            "cameras":  cameras,
            "date_from": date_from,
            "date_to": date_to,
            "time_from": time_from,
            "time_to": time_to,
            "prob_min": prob_min,
            "prob_max": prob_max,
            "sort_field": sort_field,
            "sort_order": sort_order,
        }


class CheckableComboBox(QComboBox):
    def __init__(self, items=None):
        super().__init__()
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setAlignment(Qt.AlignLeft)
        self.checked_items = []

        if items:
            for item in items:
                self.addItem(item, checked=True)

    def addItem(self, text, checked=True):
        super().addItem(text)
        index = self.count() - 1
        item_model = self.model().item(index, 0)
        item_model.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
        item_model.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.update_text()

    def update_text(self):
        checked_texts = []
        for i in range(self.count()):
            item = self.model().item(i, 0)
            if item.checkState() == Qt.Checked:
                checked_texts.append(item.text())

        if len(checked_texts) == self.count():
            self.lineEdit().setText("Все")
        else:
            self.lineEdit().setText(", ".join(checked_texts))

    def hidePopup(self):
        self.update_text()
        super().hidePopup()


class RangeSlider(QWidget):
    valueChanged = pyqtSignal(int, int)

    def __init__(self, minimum=0, maximum=100, parent=None):
        super().__init__(parent)
        self.min_value = minimum
        self.max_value = maximum

        self.label_title = QLabel("Вероятность:")
        self.label_title.setStyleSheet("color: #ffffff; font-weight: bold;")

        self.slider_min = QSlider(Qt.Horizontal)
        self.slider_max = QSlider(Qt.Horizontal)

        for slider in (self.slider_min, self.slider_max):
            slider.setRange(minimum, maximum)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 6px;
                    background: #2a2e35;
                    border-radius: 3px;
                }
                QSlider::handle:horizontal {
                    background: #3a7fff;
                    border: 1px solid #3a7fff;
                    width: 16px;
                    margin: -5px 0;
                    border-radius: 8px;
                }
            """)

        self.slider_min.setValue(minimum)
        self.slider_max.setValue(maximum)

        self.label_range = QLabel(f"{self.min_value}% – {self.max_value}%")
        self.label_range.setStyleSheet("color: #ffffff; font-weight: bold;")

        self.slider_min.valueChanged.connect(self.update_min)
        self.slider_max.valueChanged.connect(self.update_max)

        layout = QHBoxLayout(self)
        layout.addWidget(self.label_title)
        layout.addWidget(self.slider_min)
        layout.addWidget(self.slider_max)
        layout.addWidget(self.label_range)


    def update_min(self, value):
        if value > self.max_value:
            self.slider_min.setValue(self.max_value)
            self.min_value = self.max_value
        else:
            self.min_value = value
        self.label_range.setText(f"{self.min_value}% – {self.max_value}%")
        self.valueChanged.emit(self.min_value, self.max_value)

    def update_max(self, value):
        if value < self.min_value:
            self.slider_max.setValue(self.min_value)
            self.max_value = self.min_value
        else:
            self.max_value = value
        self.label_range.setText(f"{self.min_value}% – {self.max_value}%")
        self.valueChanged.emit(self.min_value, self.max_value)

