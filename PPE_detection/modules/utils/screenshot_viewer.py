import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QScrollArea, QPushButton, QHBoxLayout, QMessageBox, QLabel
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QSize


class ScreenshotViewer(QDialog):

    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        if not os.path.exists(self.image_path):
            QMessageBox.warning(
                parent,
                "Файл не найден",
                f"Скриншот не найден:\n{self.image_path}"
            )
            self._invalid = True
            return
        else:
            self._invalid = False
        self.scroll_area = QScrollArea()
        self.close_btn = QPushButton("Закрыть")
        self.image_label = QLabel()
        self.setWindowTitle("Скриншот нарушения")
        self.setMinimumSize(1000, 800)
        self.setup_ui()
        self.load_image()


    def setup_ui(self):
        layout = QVBoxLayout(self)

        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.scroll_area)

        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setFixedWidth(100)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def load_image(self):
        if not os.path.exists(self.image_path):
            QMessageBox.warning(self, "Файл не найден", f"Скриншот не найден:\n{self.image_path}")
            self.close()
            return

        pixmap = QPixmap(self.image_path)

        scaled_pixmap = pixmap.scaled(
            self.size() - QSize(50, 50),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignCenter)

        self.scroll_area.setWidget(self.image_label)

    def resizeEvent(self, event):
        if hasattr(self, 'image_label') and self.image_label.pixmap():
            self.load_image()
        super().resizeEvent(event)
