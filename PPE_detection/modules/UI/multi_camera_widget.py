import math
import cv2
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap

class MultiCameraWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid_layout = QGridLayout(self)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(2)
        self._labels = []
        self._camera_count = 0

    def set_camera_count(self, count):
        self._camera_count = max(0, count)
        self._rebuild_grid()

    def _rebuild_grid(self):
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._labels.clear()

        if self._camera_count == 0:
            return

        cols = math.ceil(math.sqrt(self._camera_count))
        rows = math.ceil(self._camera_count / cols)

        for i in range(self._camera_count):
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(
                "background-color: #1a1f25; border: 1px solid #2a2e35; color: #8a94a6;"
            )
            label.setText(f"Камера {i+1}\n(нет сигнала)")
            self._labels.append(label)

            row = i // cols
            col = i % cols
            self._grid_layout.addWidget(label, row, col)

    def update_frame(self, camera_index, frame):
        if 0 <= camera_index < len(self._labels):
            label = self._labels[camera_index]
            if frame is not None:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                scaled = pixmap.scaled(
                    label.width(), label.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                label.setPixmap(scaled)
            else:
                label.setPixmap(QPixmap())
                label.setText(f"Камера {camera_index+1}\n(нет сигнала)")

    def update_status(self, camera_index, status_text, fps=None):
        if 0 <= camera_index < len(self._labels):
            print(f"[Камера {camera_index}] {status_text}" + (f" FPS: {fps}" if fps else ""))

    def clear_frame(self, camera_index):
        self.update_frame(camera_index, None)

    def resizeEvent(self, event):
        super().resizeEvent(event)
