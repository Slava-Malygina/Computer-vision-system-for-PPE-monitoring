from PyQt5.QtWidgets import QFrame, QWidget, QHBoxLayout, QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTransform

from modules.utils.style_loader import StyleLoader


class GradientOutlineButton(QWidget):
    def __init__(self, text, left_icon_path=None, right_icon_path=None):
        super().__init__()

        self.left_icon_path = left_icon_path
        self.right_icon_path = right_icon_path
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.outer_frame = QFrame()
        self.outer_frame.setObjectName("outerFrame")

        self.button_container = QWidget()
        self.button_container.setObjectName("buttonContainer")
        container_layout = QHBoxLayout(self.button_container)
        container_layout.setContentsMargins(15, 5, 15, 5)

        self.button_container.setObjectName("buttonContainer")
        self.left_icon = None
        if left_icon_path:
            self.left_icon = QLabel()
            self.set_left_icon(left_icon_path)
            container_layout.addWidget(self.left_icon)

        self.button_text = QLabel(text)
        self.button_text.setObjectName("buttonText")
        container_layout.addWidget(self.button_text)

        self.right_icon = None
        if right_icon_path:
            self.right_icon = QLabel()
            self.set_right_icon(right_icon_path)
            container_layout.addWidget(self.right_icon)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.outer_frame)

        outer_layout = QHBoxLayout(self.outer_frame)
        outer_layout.setContentsMargins(5, 0, 0, 0)
        outer_layout.addStretch()

        outer_layout.addWidget(self.button_container)

        self.button_container.mousePressEvent = self.on_click
        self.button_container.setCursor(Qt.PointingHandCursor)

        stylesheet = StyleLoader.load_stylesheet("switch_btn_style.qss")
        self.setStyleSheet(stylesheet)


        self.clicked_callback = None

    def set_left_icon(self, icon_path):
        if self.left_icon:
            self.left_icon.setPixmap(QPixmap(icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    def on_click(self, event):
        if self.clicked_callback:
            self.clicked_callback()
        else:
            self.clicked()
    def set_right_icon(self, icon_path):
        if self.right_icon:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():

                transform = QTransform()
                transform.rotate(180)
                rotated_pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                self.right_icon.setPixmap(rotated_pixmap.scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def set_text(self, text):
        self.button.setText(text)

    def clicked(self):
        pass