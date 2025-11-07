import sys
import os
import cv2
from ultralytics import YOLO
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                             QWidget, QLabel, QPushButton, QListWidget,
                             QSlider, QMessageBox, QSplitter, QComboBox, QFileDialog,
                             QProgressBar, QTabWidget, QGroupBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap

import time
import gc

from PPE_detection.modules.logger import ViolationLogger
from PPE_detection.modules.video_thread import VideoThread
from PPE_detection.modules.violation_detector import ViolationDetector, _iou


def get_model_path():
    possible_paths = [
        "best.pt",
        "model/best.pt",
        "resources/best.pt",
        os.path.join(os.path.dirname(__file__), "best.pt"),
        os.path.join(os.path.dirname(__file__), "model", "best.pt"),
        os.path.join(os.path.dirname(__file__), "resources", "best.pt"),
    ]

    for path in possible_paths:
        if os.path.exists(path):
            return path

    return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.video_thread = None
        self.current_frame = None
        self.is_detecting = False
        self.violations_log = []
        self.available_cameras = []
        self.violation_detector = ViolationDetector()
        self.violation_logger = ViolationLogger()
        self.tracked_objects = []
        self.frame_counter = 0
        self.processing_frame = False
        self.last_detection_time = 0
        self.detection_interval = 1

        self.last_detections = []
        self.last_tracks = []
        self.last_violations = {}

        self.init_ui()
        self.load_model()
        self.detect_cameras()
        self.setup_timers()

    def init_ui(self):
        self.setWindowTitle("PPE Monitor - Safety Compliance System")
        self.setGeometry(100, 100, 1400, 900)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1419;
                color: #ffffff;
            }
            QWidget {
                background-color: #0f1419;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #2a2e35;
                background-color: #1a1f25;
            }
            QTabBar::tab {
                background-color: #2a2e35;
                color: #8a94a6;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #3a7fff;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #2a2e35;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #8a94a6;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #2a2e35;
                color: #ffffff;
                border: 1px solid #3a424e;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a424e;
            }
            QPushButton:pressed {
                background-color: #3a7fff;
            }
            QPushButton:disabled {
                background-color: #1a1f25;
                color: #5a6370;
            }
            QComboBox {
                background-color: #2a2e35;
                color: #ffffff;
                border: 1px solid #3a424e;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3a424e;
                height: 6px;
                background: #2a2e35;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3a7fff;
                border: 1px solid #3a7fff;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QProgressBar {
                border: 1px solid #3a424e;
                border-radius: 4px;
                background-color: #2a2e35;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #3a7fff;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #1a1f25;
                color: #ffffff;
                border: 1px solid #2a2e35;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        tab_widget = QTabWidget()

        monitor_tab = QWidget()
        monitor_layout = QVBoxLayout(monitor_tab)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)

        title_label = QLabel("PPE MONITOR")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #3a7fff;
                padding: 10px;
            }
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)

        self.stats_label = QLabel("Violations: 0")
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
        monitor_layout.addWidget(header_widget)

        content_splitter = QSplitter(Qt.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        video_group = QGroupBox("Live Feed")
        video_layout = QVBoxLayout(video_group)

        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(800, 500)
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
        self.video_label.setText(
            "ATOM PPE MONITORING SYSTEM\n\n"
            "Real-time safety compliance detection\n"
            "Continuous bounding box display\n"
            "Anti-spam violation logging\n\n"
            "Select source and click START"
        )
        video_layout.addWidget(self.video_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        video_layout.addWidget(self.progress_bar)

        left_layout.addWidget(video_group)

        control_group = QGroupBox("Source Control")
        control_layout = QVBoxLayout(control_group)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Source:"))

        self.source_combo = QComboBox()
        self.source_combo.addItem("Camera", "camera")
        self.source_combo.addItem("Video File", "video")
        source_layout.addWidget(self.source_combo)

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(120)
        source_layout.addWidget(self.camera_combo)

        self.video_path_label = QLabel("No file selected")
        self.video_path_label.setStyleSheet("color: #8a94a6; font-size: 12px;")
        source_layout.addWidget(self.video_path_label)

        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_video_file)
        source_layout.addWidget(self.browse_btn)

        source_layout.addStretch()
        control_layout.addLayout(source_layout)

        buttons_layout = QHBoxLayout()

        self.start_btn = QPushButton("START")
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

        self.stop_btn = QPushButton("STOP")
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

        detection_group = QGroupBox("Detection Settings")
        detection_layout = QVBoxLayout(detection_group)

        detection_buttons_layout = QHBoxLayout()

        self.start_detection_btn = QPushButton("START DETECTION")
        self.start_detection_btn.setMinimumHeight(35)
        self.start_detection_btn.clicked.connect(self.start_detection)
        self.start_detection_btn.setEnabled(False)
        detection_buttons_layout.addWidget(self.start_detection_btn)

        self.stop_detection_btn = QPushButton("STOP DETECTION")
        self.stop_detection_btn.setMinimumHeight(35)
        self.stop_detection_btn.clicked.connect(self.stop_detection)
        self.stop_detection_btn.setEnabled(False)
        detection_buttons_layout.addWidget(self.stop_detection_btn)

        detection_layout.addLayout(detection_buttons_layout)

        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence Threshold:"))

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

        self.status_label = QLabel("System Ready")
        self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        info_layout.addWidget(self.status_label)

        self.fps_label = QLabel("FPS: 0")
        info_layout.addWidget(self.fps_label)

        self.model_label = QLabel("Model: Loading...")
        info_layout.addWidget(self.model_label)

        info_layout.addStretch()
        left_layout.addWidget(info_widget)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        violations_group = QGroupBox("Violations Log")
        violations_layout = QVBoxLayout(violations_group)

        self.violations_list = QListWidget()
        violations_layout.addWidget(self.violations_list)

        log_buttons_layout = QHBoxLayout()

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.clear_journal)
        log_buttons_layout.addWidget(self.clear_btn)

        self.export_btn = QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.export_journal)
        log_buttons_layout.addWidget(self.export_btn)

        violations_layout.addLayout(log_buttons_layout)
        right_layout.addWidget(violations_group)

        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setSizes([800, 400])

        monitor_layout.addWidget(content_splitter)

        tab_widget.addTab(monitor_tab, "Monitoring")

        main_layout.addWidget(tab_widget)

    def setup_timers(self):
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.update_display)
        self.fps_counter = 0
        self.last_fps_time = time.time()

    def detect_cameras(self):
        print("Scanning for available cameras...")
        self.available_cameras = []

        for i in range(3):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    self.available_cameras.append(i)
                    self.camera_combo.addItem(f"Camera {i}", i)
                cap.release()
                del cap
                gc.collect()

        if not self.available_cameras:
            self.camera_combo.addItem("No cameras found", -1)

    def load_model(self):
        try:
            model_path = get_model_path()

            if model_path and os.path.exists(model_path):
                if hasattr(self, 'model'):
                    del self.model
                gc.collect()

                self.model = YOLO(model_path)
                model_name = os.path.basename(model_path)
                self.model_label.setText(f"Model: {model_name}")
            else:
                self.model = YOLO('../../yolov8n.pt')
                self.model_label.setText("Model: YOLOv8n (Demo)")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load model: {e}")
            self.model = None

    def browse_video_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*.*)"
        )
        if filename:
            self.video_path_label.setText(os.path.basename(filename))
            self.video_path_label.setToolTip(filename)
            self.current_video_path = filename

    def start_video(self):
        source_type = self.source_combo.currentData()

        if source_type == "camera":
            if not self.available_cameras:
                QMessageBox.warning(self, "Warning", "No cameras available!")
                return
            source_path = self.camera_combo.currentData()
            if source_path == -1:
                QMessageBox.warning(self, "Warning", "No valid camera selected!")
                return
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
            self.video_thread.wait(2000)

        self.display_timer.stop()

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.start_detection_btn.setEnabled(False)
        self.stop_detection_btn.setEnabled(False)

        self.video_label.setText("ATOM PPE MONITORING SYSTEM\n\nSelect source and click START")
        self.status_label.setText("System Ready")
        self.fps_label.setText("FPS: 0")
        self.progress_bar.setVisible(False)

        self.current_frame = None
        gc.collect()

    def on_video_finished(self):
        self.stop_video()
        self.status_label.setText("Video processing completed")

    def start_detection(self):
        if not self.model:
            QMessageBox.warning(self, "Warning", "Model not loaded!")
            return

        self.is_detecting = True
        self.status_label.setText("Detection ACTIVE")

        self.start_detection_btn.setEnabled(False)
        self.stop_detection_btn.setEnabled(True)

    def stop_detection(self):
        self.is_detecting = False

        self.start_detection_btn.setEnabled(True)
        self.stop_detection_btn.setEnabled(False)
        self.status_label.setText("Detection stopped")

    def on_frame_received(self, frame):
        self.current_frame = frame

        if self.is_detecting and self.model is not None and not self.processing_frame:
            current_time = time.time()
            if current_time - self.last_detection_time >= self.detection_interval:
                self.last_detection_time = current_time
                self.processing_frame = True

                try:
                    processed_frame, violations, detections, tracks = self.process_frame_with_detection(frame)
                    self.last_detections = detections
                    self.last_tracks = tracks

                    for violation in violations:
                        self.add_violation(violation)

                except Exception as e:
                    print(f"Detection error: {e}")
                finally:
                    self.processing_frame = False
                    gc.collect()

    def process_frame_with_detection(self, frame):
        violations = []
        processed_frame = frame.copy()
        detections = []
        tracks = []

        try:
            detection_frame = cv2.resize(frame, (640, 480))

            results = self.model(detection_frame,
                                 conf=self.conf_slider.value() / 100.0,
                                 verbose=False,
                                 imgsz=640)

            if len(results) > 0 and results[0].boxes is not None:
                scale_x = frame.shape[1] / detection_frame.shape[1]
                scale_y = frame.shape[0] / detection_frame.shape[0]

                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    x1 = int(x1 * scale_x)
                    y1 = int(y1 * scale_y)
                    x2 = int(x2 * scale_x)
                    y2 = int(y2 * scale_y)

                    detections.append({
                        'cls': class_name,
                        'bbox': [x1, y1, x2, y2],
                        'conf': conf
                    })

                self.frame_counter += 1
                tracks = self.simple_tracking(detections)
                self.tracked_objects = tracks

                result = self.violation_detector.process_frame(
                    detections, tracks, self.frame_counter
                )

                self.last_violations = result['violations_dict']

                for human_id, human_violations in result['violations_dict'].items():
                    for violation in human_violations:
                        violations.append({
                            'timestamp': datetime.now().strftime("%H:%M:%S"),
                            'class': violation['violation_type'],
                            'confidence': f"{violation['probability']:.3f}",
                            'human_id': human_id,
                        })

                        self.violation_logger.add_frame_violations(
                            self.frame_counter,
                            {human_id: [violation]},
                            None
                        )

        except Exception as e:
            print(f"Processing error: {e}")

        return processed_frame, violations, detections, tracks

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

    def simple_tracking(self, detections, iou_threshold=0.5):
        current_tracks = []

        person_detections = [det for det in detections if det['cls'] in ['human', 'person']]

        for det in person_detections:
            x1, y1, x2, y2 = det['bbox']

            best_match = None
            best_iou = 0

            for track in self.tracked_objects:
                track_box = [track[0], track[1], track[2], track[3]]
                det_box = [x1, y1, x2, y2]
                iou_val = _iou(track_box, det_box)

                if iou_val > best_iou and iou_val > iou_threshold:
                    best_iou = iou_val
                    best_match = track

            if best_match:
                track_id = best_match[4]
                current_tracks.append((x1, y1, x2, y2, track_id))
            else:
                track_id = len(self.tracked_objects) + 1
                current_tracks.append((x1, y1, x2, y2, track_id))

        return current_tracks

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
        self.stats_label.setText(f"Violations: {unique_violations}")

        print(f"{log_entry}")

    def clear_journal(self):
        self.violations_list.clear()
        self.violations_log.clear()
        self.violation_detector.clear_recorded_violations()
        self.last_violations.clear()
        self.stats_label.setText("Violations: 0")
        print("Log cleared")

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
                print(f"Exported to {filename}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def confidence_changed(self, value):
        conf_value = value / 100.0
        self.conf_label.setText(f"{conf_value:.2f}")

    def closeEvent(self, event):
        self.stop_video()
        if hasattr(self, 'violation_logger'):
            self.violation_logger.flush()
        if hasattr(self, 'model'):
            del self.model
        gc.collect()
        event.accept()


def main():
    gc.collect()

    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    result = app.exec_()

    gc.collect()
    return result


if __name__ == "__main__":
    main()
