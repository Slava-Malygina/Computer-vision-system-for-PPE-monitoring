import cv2
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap


class UIHandler:
    def __init__(self, multi_camera_widget, single_video_label=None,
                 violations_list=None,
                 status_label=None,
                 stats_label=None,
                 conf_label=None):

        self.multi_camera_widget = multi_camera_widget
        self.single_video_label = single_video_label
        self.violations_list = violations_list
        self.status_label = status_label
        self.stats_label = stats_label
        self.conf_label = conf_label
        self.violations_log = []

    def update_frame(self, camera_index, frame):
        """Обновление кадра в многокамерном виджете"""
        self.multi_camera_widget.update_frame(camera_index, frame)

    def update_single_frame(self, frame):
        """Обновление виджета одиночного видео"""
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            scaled_pixmap = pixmap.scaled(
                self.single_video_label.width() - 10,
                self.single_video_label.height() - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.single_video_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"Display error: {e}")

    def update_fps(self, camera_index, fps):
        """Обновление FPS в интерфейсе"""
        self.multi_camera_widget.update_fps(camera_index, fps)

    def update_status(self, status_text):
        """Обновление статусной строки"""
        self.status_label.setText(status_text)

    def update_confidence_label(self, conf_value):
        """Обновление порога уверенности"""
        self.conf_label.setText(f"{conf_value:.2f}")

    def add_violation(self, violation):
        """Добавление нарушения в список"""
        self.violations_log.append(violation)

        timestamp = violation['timestamp']
        violation_type = violation['class']
        confidence = violation['confidence']
        human_id = violation['human_id']

        log_entry = f"[{timestamp}] {violation_type} (ID: {human_id}) - {confidence}"

        self.violations_list.addItem(log_entry)
        self.violations_list.scrollToBottom()

        unique_violations = len(self.violations_log)
        self.stats_label.setText(f"Нарушения: {unique_violations}")

    def clear_journal(self):
        """Очистка журнала нарушений"""
        self.violations_list.clear()
        self.violations_log.clear()
        self.stats_label.setText("Нарушения: 0")