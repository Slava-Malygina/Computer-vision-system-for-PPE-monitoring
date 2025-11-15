import csv
import os

from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QWidget, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QComboBox)

from PPE_detection.modules.UI.filter_panel import FilterPanel
from PPE_detection.modules.UI.pagination_panel import PaginationPanel

from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt, QSize


class ViolationLogsTab(QWidget):
    def __init__(self, master_log_path="../../logs/main_log.csv"):
        super().__init__()
        self.master_log_path = master_log_path
        self.data_loaded = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        horizontal_layout = QHBoxLayout(self)
        log_layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setItemDelegate(PaddingDelegate(left=8))

        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Дата", "Время", "ID нарушителя", "Вероятность нарушения", "Путь к скриншоту"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
                    QTableWidget {
                        background-color: #1a1f25;
                        alternate-background-color: #222831;
                        color: #ffffff;
                        border-radius: 8px; 
                        border: 1px solid #2a2e35;
                    }
                    QHeaderView::section {
                        background-color: #2a2e35;
                        color: #8a94a6;
                        padding: 6px;
                        border: none;
                    }
                        QTableWidget::item {
                        padding-left: 8px;  
                    }
                    QTableWidget::item:selected {
                        background-color: #3a7fff;
                        color: #ffffff;
                    }
                """)
        self.table.verticalHeader().setVisible(False)
        self.filter_panel = FilterPanel()

        per_page_layout = QHBoxLayout()
        per_page_layout.setAlignment(Qt.AlignRight)


        label = QLabel("Строк на странице:")
        label.setStyleSheet("color: #b0b0b0; font-size: 13px;")

        self.per_page_combo = QComboBox()
        self.per_page_combo.addItems(["10", "25", "50", "100"])
        self.per_page_combo.setCurrentText("25")
        self.per_page_combo.setFixedWidth(80)

        per_page_layout.addWidget(label)
        per_page_layout.addWidget(self.per_page_combo)

        log_layout.addLayout(per_page_layout)
        log_layout.addWidget(self.table)
        horizontal_layout.addLayout(log_layout, stretch=5)
        horizontal_layout.addWidget(self.filter_panel, stretch=2)
        main_layout.addLayout(horizontal_layout)
        self.refresh_btn = QPushButton("Обновить")


        self.refresh_btn.setIconSize(QSize(24, 24))
        self.refresh_btn.setToolTip("Обновить")
        self.refresh_btn.clicked.connect(self.reload_logs)

        self.pagination = PaginationPanel()
        pages_reload_layout = QHBoxLayout()
        pages_reload_layout.setContentsMargins(0, 5, 0, 0)

        left_layout = QHBoxLayout()
        left_layout.addWidget(self.refresh_btn)
        left_layout.addStretch()
        pages_reload_layout.addLayout(left_layout, stretch=1)

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(self.pagination)
        center_layout.addStretch()
        pages_reload_layout.addLayout(center_layout, stretch=2)

        right_layout = QHBoxLayout()
        right_layout.addStretch()
        pages_reload_layout.addLayout(right_layout, stretch=1)

        log_layout.addLayout(pages_reload_layout)


    def load_logs_once(self):
        if not self.data_loaded:
            self.reload_logs()
            self.data_loaded = True

    def reload_logs(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))  # папка, где utils.py
        log_path = os.path.join(script_dir, self.master_log_path)
        if not os.path.exists(log_path):
            print(log_path)
            return

        with open(self.master_log_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        self.table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            self.table.setItem(row_idx, 0, QTableWidgetItem(row.get("date", "")))
            self.table.setItem(row_idx, 1, QTableWidgetItem(row.get("processing_time", "")))
            self.table.setItem(row_idx, 2, QTableWidgetItem(row.get("human_id", "")))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(row.get("violation_probability", ""))))
            self.table.setItem(row_idx, 4, QTableWidgetItem(row.get("screenshot_path", "")))


class PaddingDelegate(QStyledItemDelegate):
    def __init__(self, left=8, parent=None):
        super().__init__(parent)
        self.left = left

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignVCenter | Qt.AlignLeft
        option.text = " " * (self.left // 2) + option.text