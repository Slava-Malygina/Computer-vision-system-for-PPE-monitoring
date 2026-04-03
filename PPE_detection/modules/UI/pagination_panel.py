import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton)
from PyQt5.QtCore import Qt, pyqtSignal


class PaginationPanel(QWidget):
    pageChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        left_icon_path = os.path.join(base_dir, "..", "..", "resources", "icons", "ic_arrow_back.png")
        right_icon_path = os.path.join(base_dir, "..", "..", "resources", "icons", "ic_arrow_next.png")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 10, 5, 5)
        main_layout.setSpacing(4)
        main_layout.setAlignment(Qt.AlignCenter)

        nav_layout = QHBoxLayout()
        nav_layout.setAlignment(Qt.AlignCenter)
        nav_layout.setSpacing(0)

        self.prev_btn = QPushButton(QIcon(left_icon_path), "")
        self.prev_btn.setObjectName("leftPageButton")
        self.prev_btn.setFixedSize(30, 30)
        self.prev_btn.setCursor(Qt.PointingHandCursor)

        self.page_label = QLabel("1 из 1")
        self.page_label.setObjectName("pageLabel")
        self.page_label.setAlignment(Qt.AlignCenter)

        self.next_btn = QPushButton(QIcon(right_icon_path), "")
        self.next_btn.setObjectName("rightPageButton")
        self.next_btn.setFixedSize(30, 30)
        self.next_btn.setCursor(Qt.PointingHandCursor)


        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_btn)
        main_layout.addLayout(nav_layout)

        self.prev_btn.clicked.connect(self.go_prev)
        self.next_btn.clicked.connect(self.go_next)

        self._current_page = 1
        self._total_pages = 1
        self._update_ui()

    def go_prev(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._update_ui()
            self.pageChanged.emit(self._current_page)

    def go_next(self):
        if self._current_page < self._total_pages:
            self._current_page += 1
            self._update_ui()
            self.pageChanged.emit(self._current_page)

    def set_total_pages(self, total):
        self._total_pages = max(1, total)
        if self._current_page > self._total_pages:
            self._current_page = self._total_pages
        self._update_ui()

    def set_current_page(self, page):
        self._current_page = max(1, min(page, self._total_pages))
        self._update_ui()
        self.pageChanged.emit(self._current_page)

    def _update_ui(self):
        self.page_label.setText(f"{self._current_page} из {self._total_pages}")
        self.prev_btn.setEnabled(self._current_page > 1)
        self.next_btn.setEnabled(self._current_page < self._total_pages)


