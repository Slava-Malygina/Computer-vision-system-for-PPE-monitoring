import os
import cv2
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QListWidget, QSlider, QMessageBox, QSplitter, QComboBox, QFileDialog, QProgressBar, QGroupBox, QLineEdit
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
import time
from detection_thread import DetectionThread
from logger import ViolationLogger
from video_thread import VideoThread
from violation_detector import ViolationDetector, _iou

class MonitoringTab(QWidget):
    def __init__(self, logger):
        super().__init__()
        self.model = None
        self.video_thread = None
        self.detection_thread = None
        self.current_frame = None
        self.is_detecting = False
        self.violations_log = []
        self.available_cameras = []
        self.violation_detector = ViolationDetector()
        self.violation_logger = logger
        self.track_history = []
        self.frame_counter = 0
        self.processing_frame = False
        self.last_detection_time = 0
        self.detection_interval = 0.05
        self.next_track_id = 0
        self.last_detections = []
        self.last_tracks = []
        self.last_violations = {}
        self.current_video_path = None
        self.init_ui()
        self.detect_cameras()
        self.setup_timers()
        self.load_model()

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1419;
                color: #ffffff;
            }
            QPushButton {
                background-color: #2a2e35;
                color: #ffffff;
                border: 1px solid #3a424e;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
        """)

        monitor_layout = QVBoxLayout(self)
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(2, 2, 2, 2)
        header_layout.addStretch()
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)

        self.stats_label = QLabel("Нарушения: 0")
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                padding: 8px 16px;
                background-color: #2a2e35;
                border-radius: 4px;
            }
        """)
        stats_layout.addWidget(self.stats_label)

        header_layout.addWidget(stats_widget)

        content_splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        video_group = QGroupBox("Мониторинг")
        video_layout = QVBoxLayout(video_group)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(700, 500)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1a1f25;
                border: 2px solid #2a2e35;
                border-radius: 6px;
                color: #8a94a6;
                font-size: 14px;
                qproperty-alignment: AlignCenter;
            }
        """)
        self.video_label.setText("Выберите источник видеопотока")
        video_layout.addWidget(self.video_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        video_layout.addWidget(self.progress_bar)

        left_layout.addWidget(video_group)

        control_group = QGroupBox("")
        control_layout = QVBoxLayout(control_group)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Источник:"))

        self.source_combo = QComboBox()
        self.source_combo.addItem("Камера", "camera")
        self.source_combo.addItem("Видеофайл", "video")
        self.source_combo.addItem("IP-камера", "rtsp")
        source_layout.addWidget(self.source_combo)

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(120)
        source_layout.addWidget(self.camera_combo)

        self.video_path_label = QLabel("Файл не выбран")
        source_layout.addWidget(self.video_path_label)

        self.rtsp_edit = QLineEdit()
        self.rtsp_edit.setPlaceholderText("rtsp://...")
        self.rtsp_edit.setVisible(False)
        source_layout.addWidget(self.rtsp_edit)

        self.browse_btn = QPushButton("Выбрать...")
        self.browse_btn.clicked.connect(self.browse_video_file)
        source_layout.addWidget(self.browse_btn)

        source_layout.addStretch()
        control_layout.addLayout(source_layout)

        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        self.on_source_changed(0)

        buttons_layout = QHBoxLayout()
        self.start_btn = QPushButton("СТАРТ")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self.start_video)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        buttons_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("СТОП")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self.stop_video)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ec7063;
            }
        """)
        buttons_layout.addWidget(self.stop_btn)

        control_layout.addLayout(buttons_layout)
        left_layout.addWidget(control_group)

        detection_group = QGroupBox("Детекция")
        detection_layout = QVBoxLayout(detection_group)

        detection_buttons_layout = QHBoxLayout()
        self.start_detection_btn = QPushButton("НАЧАТЬ РАСПОЗНАВАНИЕ")
        self.start_detection_btn.setMinimumHeight(35)
        self.start_detection_btn.clicked.connect(self.start_detection)
        self.start_detection_btn.setEnabled(False)
        detection_buttons_layout.addWidget(self.start_detection_btn)

        self.stop_detection_btn = QPushButton("ОСТАНОВИТЬ РАСПОЗНАВАНИЕ")
        self.stop_detection_btn.setMinimumHeight(35)
        self.stop_detection_btn.clicked.connect(self.stop_detection)
        self.stop_detection_btn.setEnabled(False)
        detection_buttons_layout.addWidget(self.stop_detection_btn)

        detection_layout.addLayout(detection_buttons_layout)

        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Порог уверенности:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 95)
        self.conf_slider.setValue(70)
        self.conf_slider.valueChanged.connect(self.on_confidence_changed)
        confidence_layout.addWidget(self.conf_slider)
        self.conf_label = QLabel("0.70")
        self.conf_label.setMinimumWidth(40)
        confidence_layout.addWidget(self.conf_label)

        detection_layout.addLayout(confidence_layout)
        left_layout.addWidget(detection_group)

        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        info_layout.addWidget(self.status_label)
        self.fps_label = QLabel("FPS: 0")
        info_layout.addWidget(self.fps_label)
        self.model_label = QLabel("Модель: загрузка...")
        info_layout.addWidget(self.model_label)
        info_layout.addStretch()
        left_layout.addWidget(info_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        violations_group = QGroupBox("Последние нарушения")
        violations_layout = QVBoxLayout(violations_group)
        self.violations_list = QListWidget()
        violations_layout.addWidget(self.violations_list)

        log_buttons_layout = QHBoxLayout()
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear_journal)
        log_buttons_layout.addWidget(self.clear_btn)
        self.export_btn = QPushButton("Экспорт CSV")
        self.export_btn.clicked.connect(self.export_journal)
        log_buttons_layout.addWidget(self.export_btn)

        violations_layout.addLayout(log_buttons_layout)
        right_layout.addWidget(violations_group)
        right_layout.addWidget(header_widget)

        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([800, 400])

        monitor_layout.addWidget(content_splitter)

    def on_source_changed(self, index):
        source_type = self.source_combo.currentData()
        self.camera_combo.setVisible(False)
        self.video_path_label.setVisible(False)
        self.browse_btn.setVisible(False)
        self.rtsp_edit.setVisible(False)

        if source_type == 'camera':
            self.camera_combo.setVisible(True)
        elif source_type == 'video':
            self.video_path_label.setVisible(True)
            self.browse_btn.setVisible(True)
        elif source_type == 'rtsp':
            self.rtsp_edit.setVisible(True)

    def detect_cameras(self):
        self.camera_combo.clear()
        self.camera_combo.addItem("Устройство 0", 0)
        self.available_cameras = [0]

    def browse_video_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Выбрать файл", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*.*)"
        )
        if filename:
            self.video_path_label.setText(os.path.basename(filename))
            self.video_path_label.setToolTip(filename)
            self.current_video_path = filename

    def start_video(self):
        source_type = self.source_combo.currentData()

        if source_type == 'camera':
            source_path = self.camera_combo.currentData()
        elif source_type == 'video':
            if not hasattr(self, 'current_video_path') or not self.current_video_path:
                QMessageBox.warning(self, "Warning", "Please select a video file first!")
                return
            source_path = self.current_video_path
        elif source_type == 'rtsp':
            source_path = self.rtsp_edit.text().strip()
            if not source_path:
                QMessageBox.warning(self, "Warning", "Please enter RTSP URL!")
                return
        else:
            return

        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()

        self.video_thread = VideoThread(source_type, source_path)
        self.video_thread.frame_ready.connect(self.on_frame_received)
        self.video_thread.status_update.connect(self.status_label.setText)
        self.video_thread.progress_update.connect(self.progress_bar.setValue)
        self.video_thread.finished_signal.connect(self.on_video_finished)
        self.video_thread.error_occurred.connect(self.on_video_error)

        if source_type == 'video':
            self.progress_bar.setVisible(True)
        else:
            self.progress_bar.setVisible(False)

        self.video_thread.start()

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.start_detection_btn.setEnabled(True)

        self.display_timer.start(67)

    def stop_video(self):
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait(1000)

        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.wait(1000)

        self.display_timer.stop()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start_detection_btn.setEnabled(False)
        self.stop_detection_btn.setEnabled(False)

        self.video_label.setText("\n\nВыберите источник видеопотока")
        self.status_label.setText("")
        self.fps_label.setText("FPS: 0")
        self.progress_bar.setVisible(False)

        self.current_frame = None

    def on_video_finished(self):
        self.stop_video()
        self.status_label.setText("Завершено")

    def on_video_error(self, error_msg):
        self.status_label.setText(f"Ошибка: {error_msg}")
        self.stop_video()

    def start_detection(self):
        if not self.model:
            QMessageBox.warning(self, "Warning", "Model not loaded!")
            return

        self.is_detecting = True
        self.status_label.setText("В процессе")
        self.start_detection_btn.setEnabled(False)
        self.stop_detection_btn.setEnabled(True)

    def stop_detection(self):
        self.is_detecting = False
        self.start_detection_btn.setEnabled(True)
        self.stop_detection_btn.setEnabled(False)
        self.status_label.setText("Остановлено")

    def on_frame_received(self, frame):
        self.current_frame = frame

        if self.is_detecting and self.model is not None and not self.processing_frame:
            current_time = time.time()
            if current_time - self.last_detection_time >= self.detection_interval:
                self.last_detection_time = current_time
                self.processing_frame = True

                self.detection_thread = DetectionThread(
                    self.model, frame, self.conf_slider.value() / 100.0, self.frame_counter
                )
                self.detection_thread.detection_done.connect(self.on_detection_done)
                self.detection_thread.start()

    def on_detection_done(self, detections, frame, frame_counter, results):
        try:
            violations = []
            tracks = self.simple_tracking(detections)

            result = self.violation_detector.process_frame(
                detections, tracks, frame_counter
            )

            self.last_violations = result['violations_dict']
            self.last_detections = detections
            self.last_tracks = tracks
            self.frame_counter += 1

            for human_id, human_violations in result['violations_dict'].items():
                for violation in human_violations:
                    violations.append({
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'class': violation['violation_type'],
                        'confidence': f"{violation['probability']:.3f}",
                        'human_id': human_id,
                    })

                    self.violation_logger.add_frame_violations(
                        frame_counter,
                        {human_id: [violation]},
                        result["screenshot_path"]
                    )

            for violation in violations:
                self.add_violation(violation)

        except Exception as e:
            print(f"Detection processing error: {e}")
        finally:
            self.processing_frame = False

    def simple_tracking(self, detections, iou_threshold=0.3):
        current_tracks = []
        used_track_ids = set()
        current_time = time.time()

        self.track_history = [track for track in self.track_history
                              if current_time - track[5] < 30.0]

        person_detections = [det for det in detections if det['cls'] in ['person']]

        active_tracks = [track for track in self.track_history
                         if current_time - track[5] < 5.0]
        inactive_tracks = [track for track in self.track_history
                           if current_time - track[5] >= 5.0]

        unmatched_detections = []

        for det in person_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]
            det_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            best_match = None
            best_score = 0

            for track in active_tracks:
                track_box = [track[0], track[1], track[2], track[3]]
                track_id = track[4]

                if track_id in used_track_ids:
                    continue

                iou_val = _iou(track_box, det_box)

                track_center = ((track[0] + track[2]) / 2, (track[1] + track[3]) / 2)
                distance = ((det_center[0] - track_center[0]) ** 2 +
                            (det_center[1] - track_center[1]) ** 2) ** 0.5

                normalized_distance = max(0, 1 - distance / 300)

                if iou_val > 0.1:
                    score = iou_val * 0.7 + normalized_distance * 0.3
                else:
                    score = normalized_distance * 0.5

                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = track

            if best_match:
                track_id = best_match[4]
                alpha = 0.3
                smoothed_x1 = int(alpha * x1 + (1 - alpha) * best_match[0])
                smoothed_y1 = int(alpha * y1 + (1 - alpha) * best_match[1])
                smoothed_x2 = int(alpha * x2 + (1 - alpha) * best_match[2])
                smoothed_y2 = int(alpha * y2 + (1 - alpha) * best_match[3])

                current_tracks.append((smoothed_x1, smoothed_y1, smoothed_x2, smoothed_y2, track_id, current_time))
                used_track_ids.add(track_id)
            else:
                unmatched_detections.append(det)

        remaining_detections = []

        for det in unmatched_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]
            det_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            best_match = None
            best_score = 0

            for track in inactive_tracks:
                track_box = [track[0], track[1], track[2], track[3]]
                track_id = track[4]

                if track_id in used_track_ids:
                    continue

                iou_val = _iou(track_box, det_box)

                track_center = ((track[0] + track[2]) / 2, (track[1] + track[3]) / 2)
                distance = ((det_center[0] - track_center[0]) ** 2 +
                            (det_center[1] - track_center[1]) ** 2) ** 0.5

                normalized_distance = max(0, 1 - distance / 400)

                score = iou_val * 0.6 + normalized_distance * 0.4

                if score > best_score and score > 0.4:
                    best_score = score
                    best_match = track

            if best_match:
                track_id = best_match[4]
                current_tracks.append((x1, y1, x2, y2, track_id, current_time))
                used_track_ids.add(track_id)
            else:
                remaining_detections.append(det)

        for det in remaining_detections:
            x1, y1, x2, y2 = det['bbox']

            is_duplicate = False
            det_box = [x1, y1, x2, y2]
            det_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            for existing_track in current_tracks:
                existing_box = [existing_track[0], existing_track[1], existing_track[2], existing_track[3]]
                existing_center = ((existing_track[0] + existing_track[2]) / 2,
                                   (existing_track[1] + existing_track[3]) / 2)

                iou_val = _iou(existing_box, det_box)
                distance = ((det_center[0] - existing_center[0]) ** 2 +
                            (det_center[1] - existing_center[1]) ** 2) ** 0.5

                if iou_val > 0.5 or distance < 50:
                    is_duplicate = True
                    break

            if not is_duplicate:
                self.next_track_id += 1
                track_id = self.next_track_id
                current_tracks.append((x1, y1, x2, y2, track_id, current_time))
                used_track_ids.add(track_id)

        updated_history = []

        for track in current_tracks:
            updated_history.append(track)

        for track in active_tracks:
            if track[4] not in used_track_ids and current_time - track[5] < 5.0:
                updated_history.append(track)

        inactive_to_keep = [track for track in inactive_tracks
                            if track[4] not in used_track_ids and current_time - track[5] < 15.0]
        updated_history.extend(inactive_to_keep[:5])

        self.track_history = updated_history

        return [(x1, y1, x2, y2, track_id) for x1, y1, x2, y2, track_id, _ in current_tracks]

    def draw_detections_on_frame(self, frame, detections, tracks, violations_dict):
        display_frame = frame.copy()

        colors = {
            'helmet': (0, 255, 0),
            'vest': (255, 0, 0),
            'gloves': (0, 255, 255),
            'human': (255, 0, 255),
            'person': (255, 0, 255),
            'head': (255, 255, 0),
            'body': (0, 165, 255),
            'palm': (128, 0, 128),
            'wrist': (255, 165, 0),
        }

        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            class_name = det['cls']
            conf = det['conf']

            color = colors.get(class_name, (255, 255, 255))
            label = f"{class_name} {conf:.2f}"

            cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(display_frame, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        for x1, y1, x2, y2, track_id in tracks:
            human_id = f'human_{track_id}'
            track_color = (0, 255, 255)

            if human_id in violations_dict:
                violations_list = violations_dict[human_id]
                if any(v['violation_type'] == 'no_helmet' for v in violations_list):
                    track_color = (0, 0, 255)
                elif any(v['violation_type'] == 'no_vest' for v in violations_list):
                    track_color = (0, 165, 255)
                elif any(v['violation_type'] == 'no_gloves' for v in violations_list):
                    track_color = (255, 0, 0)

            cv2.rectangle(display_frame, (x1, y1), (x2, y2), track_color, 2)

            violation_text = ""
            if human_id in violations_dict:
                violations_list = violations_dict[human_id]
                violation_text = " | ".join([v['violation_type'] for v in violations_list])

            display_text = f"ID:{track_id}"
            if violation_text:
                display_text += f" | {violation_text}"

            cv2.putText(display_frame, display_text, (x1, y1 - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, track_color, 2)

        return display_frame

    def update_display(self):
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps_label.setText(f"FPS: {self.fps_counter}")
            self.fps_counter = 0
            self.last_fps_time = current_time

        if self.current_frame is not None:
            display_frame = self.current_frame.copy()

            if hasattr(self, 'last_detections') and hasattr(self, 'last_tracks'):
                display_frame = self.draw_detections_on_frame(
                    display_frame,
                    self.last_detections,
                    self.last_tracks,
                    self.last_violations
                )

            self.display_frame(display_frame)

    def display_frame(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w

            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)

            scaled_pixmap = pixmap.scaled(
                self.video_label.width() - 10,
                self.video_label.height() - 10,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled_pixmap)

        except Exception as e:
            print(f"Display error: {e}")

    def add_violation(self, violation):
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
        self.violations_list.clear()
        self.violations_log.clear()
        self.violation_detector.clear_recorded_violations()
        self.last_violations.clear()
        self.track_history.clear()
        self.next_track_id = 0
        self.stats_label.setText("Нарушения 0")

    def export_journal(self):
        if not self.violations_log:
            QMessageBox.information(self, "Info", "No violations to export!")
            return

        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Log", "ppe_violations_log.csv", "CSV Files (*.csv)"
            )

            if filename:
                df = pd.DataFrame(self.violations_log)
                df.to_csv(filename, index=False)
                QMessageBox.information(self, "Success", f"Exported to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def on_confidence_changed(self, value):
        conf_value = value / 100.0
        self.conf_label.setText(f"{conf_value:.2f}")

    def closeEvent(self, event):
        self.stop_video()
        if hasattr(self, 'violation_logger'):
            self.violation_logger.flush()
        event.accept()

    def setup_timers(self):
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.fps_counter = 0
        self.last_fps_time = time.time()

    def load_model(self):
        from model_loader import ModelLoader
        try:
            loader = ModelLoader()
            self.model = loader.load()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load model: {e}")
            self.model = None