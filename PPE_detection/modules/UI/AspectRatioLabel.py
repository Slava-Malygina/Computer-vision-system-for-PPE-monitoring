from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QSizePolicy, QWidget


class AspectRatioLabel(QLabel):
    def __init__(self, aspect_ratio=16 / 9, parent=None):
        super().__init__(parent)
        self.aspect_ratio = aspect_ratio

        self.setStyleSheet("""
            QLabel {
                background-color: #323055;
                border-radius: 6px;
                color: #8a94a6;
                 padding: 0px;          
                margin: 0px;           
                font-size: 14px;
            }

        """)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(0, 0)
        self.setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def resizeEvent(self, event):
        if self.parent():
            parent_width = self.parent().width()
            parent_height = self.parent().height()

            if parent_width > 0 and parent_height > 0:

                if parent_width / parent_height > self.aspect_ratio:
                    new_height = parent_height
                    new_width = int(new_height * self.aspect_ratio)

                else:
                    new_width = parent_width
                    new_height = int(new_width / self.aspect_ratio)

                self.setFixedSize(new_width, new_height)
                x = (parent_width - new_width) // 2
                y = (parent_height - new_height) // 2

                self.move(x, y)
        super().resizeEvent(event)


class ResizeWatcher(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        for child in self.findChildren(AspectRatioLabel):
            child.resizeEvent(None)
        super().resizeEvent(event)