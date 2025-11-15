from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QComboBox)
from PyQt5.QtCore import Qt


class PaginationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 10, 5, 5)
        main_layout.setSpacing(4)
        main_layout.setAlignment(Qt.AlignCenter)

        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignCenter)
        nav_layout.setSpacing(10)

        self.prev_btn = QPushButton("⟨")
        self.prev_btn.setFixedSize(30, 30)
        self.prev_btn.setCursor(Qt.PointingHandCursor)

        self.page_label = QLabel("1 of 1")
        self.page_label.setAlignment(Qt.AlignCenter)
        self.page_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #e0e0e0;")

        self.next_btn = QPushButton("⟩")
        self.next_btn.setFixedSize(30, 30)
        self.next_btn.setCursor(Qt.PointingHandCursor)

        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_btn)
        main_layout.addLayout(nav_layout)


        self.setStyleSheet("""
            QPushButton {
                background-color: #2b2f36;
                color: #ffffff;
                border: 1px solid #444a55;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a3f49;
                border: 1px solid #5a6472;
            }
            QPushButton:pressed {
                background-color: #4a7cff;
                border: 1px solid #4a7cff;
            }
            QLabel {
                color: #e0e0e0;
            }
            QComboBox {
                background-color: #2b2f36;
                color: #ffffff;
                border: 1px solid #555b66;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
            }
            QComboBox:hover {
                background-color: #353a43;
            }
        """)

