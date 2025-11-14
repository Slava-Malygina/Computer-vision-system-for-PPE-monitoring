import sys
import os
import cv2
import torch
from ultralytics import YOLO
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QListWidget,
                             QSlider, QMessageBox, QSplitter, QComboBox, QFileDialog,
                             QProgressBar, QTabWidget, QFrame, QGroupBox)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon
import numpy as np
import time
import csv
import logging
from collections import defaultdict
import gc

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

def _is_inside(small_box, big_box, threshold=0.5):
    x1, y1, x2, y2 = small_box
    bx1, by1, bx2, by2 = big_box

    inter_x1 = max(x1, bx1)
    inter_y1 = max(y1, by1)
    inter_x2 = min(x2, bx2)
    inter_y2 = min(y2, by2)

    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    small_area = (x2 - x1) * (y2 - y1)
    if small_area == 0:
        return False

    return (inter_area / small_area) >= threshold

def _iou(boxA, boxB):
    x_a = max(boxA[0], boxB[0])
    y_a = max(boxA[1], boxB[1])
    x_b = min(boxA[2], boxB[2])
    y_b = min(boxA[3], boxB[3])
    inter_area = max(0, x_b - x_a) * max(0, y_b - y_a)
    box_a_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    box_b_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return inter_area / float(box_a_area + box_b_area - inter_area + 1e-6)

class ViolationLogger:
    def __init__(self, output_dir='logs', filename=None, max_buffer_size=50):
        self.output_dir = output_dir
        self.max_buffer_size = max_buffer_size
        self.buffer = []
        self.frame_counter = 0
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.logger = self._setup_logging()

        try:
            os.makedirs(output_dir, exist_ok=True)
        except (OSError, PermissionError) as e:
            self.logger.error(f"Error creating directory {output_dir}: {e}")
            raise

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'violations_log_{timestamp}.csv'

        self.file_path = os.path.join(output_dir, filename)

        try:
            self.fields = ['date', 'frame_id', 'human_id', 'processing_time', 'violation_type',
                           'violation_probability', 'screenshot_path']
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Error initializing log file {self.file_path}: {e}")
            raise

    def _setup_logging(self):
        logger = logging.getLogger(f"ViolationLogger_{id(self)}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _get_current_time(self):
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        if current_date != self.current_date:
            self.current_date = current_date

        return now.strftime('%H:%M:%S.%f')[:-3]

    def add_frame_violations(self, frame_id: int, violations_dict: dict, screenshot_path: str = None):
        try:
            if not violations_dict or not isinstance(violations_dict, dict):
                return

            for human_id, human_violations in violations_dict.items():
                if not isinstance(human_violations, list):
                    continue

                for v in human_violations:
                    self.buffer.append({
                        "date": self.current_date,
                        "frame_id": frame_id,
                        "processing_time": self._get_current_time(),
                        "violation_type": v.get('violation_type', 'unknown'),
                        "violation_probability": v.get("probability", 0.0),
                        "screenshot_path": screenshot_path or '',
                        "human_id": human_id
                    })
                    
            if len(self.buffer) >= self.max_buffer_size:
                self.flush()

        except Exception as e:
            self.logger.error(f"Error adding violations for frame_id {frame_id}: {e}")

    def _flush_buffer(self):
        if not self.buffer:
            return True
        try:
            with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writerows(self.buffer)

            self.buffer.clear()
            gc.collect()
            return True

        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Error writing buffer to file: {e}")
            return False

    def flush(self):
        return self._flush_buffer()

    def get_file_path(self):
        return self.file_path

class ViolationDetector:
    def __init__(self, overlap_thresholds=None):
        self.overlap_thresholds = overlap_thresholds or {
            'helmet': 0.4,
            'vest': 0.5,
            'gloves': 0.3,
            'head': 0.5,
            'body': 0.6,
            'palm': 0.5,
            'wrist': 0.4
        }

        self.recorded_violations = {}

    def clear_recorded_violations(self):
        self.recorded_violations.clear()

    def process_frame(self, detections, tracked_objects, frame_id):
        new_violations = {}

        objects_by_class = {}
        for det in detections:
            cls = det['cls']
            objects_by_class.setdefault(cls, []).append(det)

        helmets = objects_by_class.get('helmet', [])
        vests = objects_by_class.get('vest', [])
        gloves = objects_by_class.get('gloves', [])
        heads = objects_by_class.get('head', [])
        bodies = objects_by_class.get('body', [])
        palms = objects_by_class.get('palm', [])
        wrists = objects_by_class.get('wrist', [])

        for x1, y1, x2, y2, track_id in tracked_objects:
            person_box = [x1, y1, x2, y2]
            new_person_violations = []

            recorded_for_track = self.recorded_violations.get(track_id, set())

            head_found = [h for h in heads if _is_inside(h['bbox'], person_box, self.overlap_thresholds['head'])]
            helmet_found = [h for h in helmets if _is_inside(h['bbox'], person_box, self.overlap_thresholds['helmet'])]

            if head_found:
                head_conf = max(h['conf'] for h in head_found)
                helmet_conf = max((h['conf'] for h in helmet_found), default=0)

                if not helmet_found or (head_conf > helmet_conf):
                    violation_type = 'no_helmet'
                    probability = round(head_conf, 2)

                    if violation_type not in recorded_for_track:
                        new_person_violations.append({'violation_type': violation_type, 'probability': probability})
                        if track_id not in self.recorded_violations:
                            self.recorded_violations[track_id] = set()
                        self.recorded_violations[track_id].add(violation_type)

            body_found = [b for b in bodies if _is_inside(b['bbox'], person_box, self.overlap_thresholds['body'])]
            vest_found = [v for v in vests if _is_inside(v['bbox'], person_box, self.overlap_thresholds['vest'])]

            if body_found:
                body_conf = max(b['conf'] for b in body_found)
                vest_conf = max((v['conf'] for v in vest_found), default=0)

                if not vest_found or (body_conf > vest_conf):
                    violation_type = 'no_vest'
                    probability = round(body_conf, 2)

                    if violation_type not in recorded_for_track:
                        new_person_violations.append({'violation_type': violation_type, 'probability': probability})
                        if track_id not in self.recorded_violations:
                            self.recorded_violations[track_id] = set()
                        self.recorded_violations[track_id].add(violation_type)

            wrist_found = [w for w in wrists if _is_inside(w['bbox'], person_box, self.overlap_thresholds['wrist'])]
            glove_found = [g for g in gloves if _is_inside(g['bbox'], person_box, self.overlap_thresholds['gloves'])]

            if wrist_found:
                wrist_conf = max(w['conf'] for w in wrist_found)
                glove_conf = max((g['conf'] for g in glove_found), default=0)

                if not glove_found or (wrist_conf > glove_conf):
                    violation_type = 'no_gloves'
                    probability = round(wrist_conf, 2)

                    if violation_type not in recorded_for_track:
                        new_person_violations.append({'violation_type': violation_type, 'probability': probability})
                        if track_id not in self.recorded_violations:
                            self.recorded_violations[track_id] = set()
                        self.recorded_violations[track_id].add(violation_type)

            if new_person_violations:
                new_violations[f'human_{int(track_id)}'] = new_person_violations

        return {
            'frame_id': frame_id,
            'violations_dict': new_violations,
            'screenshot_path': None
        }

class DetectionThread(QThread):
    detection_done = pyqtSignal(object, object, object, object)
    
    def __init__(self, model, frame, conf_threshold, frame_counter):
        super().__init__()
        self.model = model
        self.frame = frame
        self.conf_threshold = conf_threshold
        self.frame_counter = frame_counter
        
    def run(self):
        try:
            results = self.model(self.frame, 
                               conf=self.conf_threshold,
                               verbose=False,
                               imgsz=640)
            
            detections = []
            if len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    detections.append({
                        'cls': class_name,
                        'bbox': [x1, y1, x2, y2],
                        'conf': conf
                    })
            
            self.detection_done.emit(detections, self.frame, self.frame_counter, results)
        except Exception as e:
            print(f"Detection error: {e}")

class VideoThread(QThread):
    frame_ready = pyqtSignal(object)
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished_signal = pyqtSignal()
    
    def __init__(self, source_type, source_path):
        super().__init__()
        self.source_type = source_type
        self.source_path = source_path
        self.is_running = False
        self.cap = None
        self.total_frames = 0
        self.current_frame = 0
        
    def run(self):
        self.is_running = True
        
        try:
            if self.source_type == 'camera':
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 15)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                if not self.cap.isOpened():
                    self.status_update.emit("Cannot open device camera")
                    return
                
                self.status_update.emit("Device camera connected")
            else:
                self.cap = cv2.VideoCapture(self.source_path)
                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.status_update.emit(f"Video loaded: {os.path.basename(self.source_path)}")
            
            while self.is_running:
                ret, frame = self.cap.read()
                if not ret:
                    if self.source_type == 'video':
                        self.status_update.emit("Video processing completed")
                        self.finished_signal.emit()
                    break
                
                if self.source_type == 'camera':
                    small_frame = frame
                else:
                    small_frame = cv2.resize(frame, (640, 480))
                    
                self.frame_ready.emit(small_frame)
                
                if self.source_type == 'video':
                    self.current_frame += 1
                    progress = int((self.current_frame / self.total_frames) * 100)
                    self.progress_update.emit(progress)
                
                time.sleep(0.033)
                
        except Exception as e:
            self.status_update.emit(f"Error: {str(e)}")
        finally:
            if self.cap is not None:
                self.cap.release()
    
    def stop(self):
        self.is_running = False
        if self.cap is not None:
            self.cap.release()

class MainWindow(QMainWindow):
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
        self.camera_combo.addItem("Device Camera", 0)
        self.available_cameras = [0]
            
    def load_model(self):
        try:
            model_path = get_model_path()
            
            if model_path and os.path.exists(model_path):
                self.model = YOLO(model_path)
                model_name = os.path.basename(model_path)
                self.model_label.setText(f"Model: {model_name}")
            else:
                self.model = YOLO('yolov8n.pt')
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
        
        self.video_label.setText("ATOM PPE MONITORING SYSTEM\n\nSelect source and click START")
        self.status_label.setText("System Ready")
        self.fps_label.setText("FPS: 0")
        self.progress_bar.setVisible(False)
        
        self.current_frame = None
        
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
                
                self.detection_thread = DetectionThread(
                    self.model, frame, self.conf_slider.value()/100.0, self.frame_counter
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
                        None
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

                score = iou_val * 0.8 + max(0, 1 - distance/150) * 0.2
                
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
            cv2.putText(display_frame, label, (x1, y1-5), 
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
            
            cv2.putText(display_frame, display_text, (x1, y1-20), 
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
        self.stats_label.setText(f"Violations: {unique_violations}")
        
    def clear_journal(self):
        self.violations_list.clear()
        self.violations_log.clear()
        self.violation_detector.clear_recorded_violations()
        self.last_violations.clear()
        self.stats_label.setText("Violations: 0")
        
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
            self.violation_logger.flush()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    
    result = app.exec_()
    
    return result

if __name__ == "__main__":
    main()