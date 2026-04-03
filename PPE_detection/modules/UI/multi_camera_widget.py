import math
import cv2
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout
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
        self._info_labels = []
        self._addresses = []
        self._fps_values = {}

    def set_camera_count(self, count):
        self._camera_count = max(0, count)
        self._rebuild_grid()

    def set_addresses(self, addresses):
        self._addresses = addresses
        self._update_info_labels()

    def update_fps(self, camera_index, fps):
        self._fps_values[camera_index] = fps
        self._update_info_labels()

    def _update_info_labels(self):
        active_indices = [i for i, addr in enumerate(self._addresses) if addr]
        for ui_idx, label in enumerate(self._info_labels):
            if ui_idx < len(active_indices):
                actual_idx = active_indices[ui_idx]
                addr = self._addresses[actual_idx]
                if len(addr) > 55:
                    display_addr = addr[:19] + "..." + addr[-19:]
                else:
                    display_addr = addr

                fps = self._fps_values.get(ui_idx, 0)
                label.setText(f"Адрес: {display_addr} | FPS: {fps:.1f}")
            else:
                label.setText("")

    def _rebuild_grid(self):
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._labels.clear()
        self._info_labels.clear()

        if self._camera_count == 0:
            return

        cols = math.ceil(math.sqrt(self._camera_count))
        rows = math.ceil(self._camera_count / cols)

        for i in range(self._camera_count):
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.setSpacing(1)
            video_label = QLabel()
            video_label.setAlignment(Qt.AlignCenter)
            video_label.setStyleSheet("background-color: #323055; border: 1px solid #2a2e35;")
            video_label.setText(f"Камера {i + 1}")
            container_layout.addWidget(video_label)
            self._labels.append(video_label)
            info_label = QLabel("")
            info_label.setStyleSheet("color: #8a94a6; font-size: 9px; background-color: #323055; padding: 2px;")
            info_label.setFixedHeight(20)

            row = i // cols
            col = i % cols

            if row == 0 and col == 0:
                info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            elif row == 0 and col == cols - 1:
                info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            elif row == rows - 1 and col == 0:
                info_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            elif row == rows - 1 and col == cols - 1:
                info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                info_label.setAlignment(Qt.AlignCenter)

            container_layout.addWidget(info_label)
            self._info_labels.append(info_label)

            self._grid_layout.addWidget(container, row, col)
        self._update_info_labels()

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
                label.setText(f"Камера {camera_index + 1}")

    def clear_frame(self, camera_index):
        self.update_frame(camera_index, None)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def clear_all(self):
        for i in range(len(self.cameras)):
            self.update_frame(i, None)


    def set_max_width(self, width):
        self.setMaximumWidth(width)