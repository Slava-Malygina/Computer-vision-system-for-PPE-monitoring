import atexit
import os
import cv2

from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import ( QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QListWidget,
                             QSlider, QMessageBox, QSplitter, QComboBox, QFileDialog,
                             QProgressBar, QGroupBox)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QImage, QPixmap
import time
from PPE_detection.modules.detection_thread import DetectionThread
from PPE_detection.modules.logger import ViolationLogger

from PPE_detection.modules.video_thread import VideoThread
from PPE_detection.modules.violation_detector import ViolationDetector, _iou


class MonitoringTab(QWidget):
    def __init__(self):
        super().__init__()
        self.model = None
        self.video_thread = None
        self.detection_thread = None
        self.current_frame = None
        self.is_detecting = False
        self.violations_log = []
        self.available_cameras = []
        self.violation_detector = ViolationDetector()
        self.violation_logger = ViolationLogger()
        atexit.register(self.violation_logger.flush)
        self.track_history = []
        self.frame_counter = 0
        self.processing_frame = False
        self.last_detection_time = 0
        self.detection_interval = 0.5
        self.next_track_id = 0

        self.last_detections = []
        self.last_tracks = []
        self.last_violations = {}

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
        self.video_label.setText("Выберите источник видеопотока"
        )
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
        source_layout.addWidget(self.source_combo)

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(120)
        source_layout.addWidget(self.camera_combo)

        self.video_path_label = QLabel("Файл не выбран")
        self.video_path_label.setStyleSheet("color: #8a94a6; font-size: 12px;")
        source_layout.addWidget(self.video_path_label)

        self.browse_btn = QPushButton("Выбрать...")
        self.browse_btn.clicked.connect(self.browse_video_file)
        source_layout.addWidget(self.browse_btn)

        source_layout.addStretch()
        control_layout.addLayout(source_layout)

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
        self.conf_slider.setValue(65)
        self.conf_slider.valueChanged.connect(self.confidence_changed)
        confidence_layout.addWidget(self.conf_slider)

        self.conf_label = QLabel("0.65")
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


    def setup_timers(self):
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.fps_counter = 0
        self.last_fps_time = time.time()

    def detect_cameras(self):
        self.camera_combo.addItem("Устройство", 0)
        self.available_cameras = [0]

    def load_model(self):
        from PPE_detection.modules.model_loader import ModelLoader
        try:
            loader = ModelLoader()
            self.model = loader.load()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load model: {e}")
            self.model = None


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

        if source_type == "camera":
            source_path = 0
        else:
            if not hasattr(self, 'current_video_path') or not self.current_video_path:
                QMessageBox.warning(self, "Warning", "Please select a video file first!")
                return
            source_path = self.current_video_path

        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()

        self.video_thread = VideoThread(source_type, source_path)
        self.video_thread.frame_ready.connect(self.on_frame_received)
        self.video_thread.status_update.connect(self.status_label.setText)
        self.video_thread.progress_update.connect(self.progress_bar.setValue)
        self.video_thread.finished_signal.connect(self.on_video_finished)

        if source_type == "video":
            self.progress_bar.setVisible(True)

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
                              if current_time - track[5] < 60.0]

        person_detections = [det for det in detections if det['cls'] in ['human', 'person']]

        active_tracks = [track for track in self.track_history
                         if current_time - track[5] < 3.0]
        inactive_tracks = [track for track in self.track_history
                           if current_time - track[5] >= 3.0]

        for det in person_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]

            best_match = None
            best_score = 0

            for track in active_tracks:
                track_box = [track[0], track[1], track[2], track[3]]
                track_id = track[4]

                if track_id in used_track_ids:
                    continue

                iou_val = _iou(track_box, det_box)

                track_center_x = (track[0] + track[2]) / 2
                track_center_y = (track[1] + track[3]) / 2
                det_center_x = (x1 + x2) / 2
                det_center_y = (y1 + y2) / 2
                distance = ((det_center_x - track_center_x) ** 2 + (det_center_y - track_center_y) ** 2) ** 0.5

                score = iou_val * 0.8 + max(0, 1 - distance / 150) * 0.2

                if score > best_score and score > 0.4:
                    best_score = score
                    best_match = track

            if best_match:
                track_id = best_match[4]
                current_tracks.append((x1, y1, x2, y2, track_id, current_time))
                used_track_ids.add(track_id)
                active_tracks = [t for t in active_tracks if t[4] != track_id]

        remaining_detections = [det for det in person_detections
                                if not any(track[4] not in used_track_ids for track in current_tracks
                                           if _iou(track[:4], det['bbox']) > 0.1)]

        for det in remaining_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]

            best_match = None
            best_score = 0

            for track in inactive_tracks:
                track_box = [track[0], track[1], track[2], track[3]]
                track_id = track[4]

                if track_id in used_track_ids:
                    continue

                iou_val = _iou(track_box, det_box)

                if iou_val > best_score and iou_val > 0.5:
                    best_score = iou_val
                    best_match = track

            if best_match:
                track_id = best_match[4]
                current_tracks.append((x1, y1, x2, y2, track_id, current_time))
                used_track_ids.add(track_id)

        for det in person_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]

            if any(_iou(track[:4], det_box) > 0.1 for track in current_tracks):
                continue

            self.next_track_id += 1
            track_id = self.next_track_id
            current_tracks.append((x1, y1, x2, y2, track_id, current_time))
            used_track_ids.add(track_id)

        updated_history = []

        for track in current_tracks:
            updated_history.append(track)

        for track in active_tracks:
            if track[4] not in used_track_ids and current_time - track[5] < 1.5:
                updated_history.append(track)

        inactive_to_keep = [track for track in inactive_tracks
                            if track[4] not in used_track_ids and current_time - track[5] < 10.0]
        updated_history.extend(inactive_to_keep[:10])

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

    def confidence_changed(self, value):
        conf_value = value / 100.0
        self.conf_label.setText(f"{conf_value:.2f}")

    def closeEvent(self, event):
        self.stop_video()
        if hasattr(self, 'violation_logger'):
            print("fff")
            self.violation_logger.flush()
        event.accept()


