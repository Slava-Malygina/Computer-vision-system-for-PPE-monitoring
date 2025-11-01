import sys
import os
import cv2
import torch
from ultralytics import YOLO
from datetime import datetime
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QPushButton, QListWidget, QFileDialog,
                             QSlider, QProgressBar, QMessageBox, QSplitter)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt5.QtGui import QImage, QPixmap
import numpy as np

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

class VideoProcessor:
    def __init__(self, model, conf_threshold=0.65):
        self.model = model
        self.conf_threshold = conf_threshold
        self.colors = {
            'helmet': (0, 255, 0),
            'vest': (255, 0, 0),  
            'glove': (0, 255, 255),
            'human': (255, 0, 255),
            'head': (255, 255, 0),
            'body': (0, 165, 255),
            'wrist': (128, 0, 128)
        }
    
    def process_frame(self, frame):
        violations = []
        
        try:
            results = self.model(frame, conf=self.conf_threshold, verbose=False)
            
            if len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls]
                    
                    violation = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'class': class_name,
                        'confidence': f"{conf:.3f}",
                        'frame_time': datetime.now()
                    }
                    violations.append(violation)
                    
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    label = f"{class_name} {conf:.2f}"
                    
                    color = self.colors.get(class_name, (255, 255, 255))
                    
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    
                    (text_width, text_height), baseline = cv2.getTextSize(
                        label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                    )
                    cv2.rectangle(frame, (x1, y1-text_height-10), 
                                (x1+text_width, y1), color, -1)
                    cv2.putText(frame, label, (x1, y1-5), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            return frame, violations
            
        except Exception as e:
            print(f"Frame processing error: {e}")
            return frame, []

class VideoAnalysisThread(QThread):
    frame_processed = pyqtSignal(object, list)
    progress_updated = pyqtSignal(int)
    analysis_finished = pyqtSignal()
    
    def __init__(self, video_path, model, conf_threshold=0.65):
        super().__init__()
        self.video_path = video_path
        self.model = model
        self.conf_threshold = conf_threshold
        self.is_running = True
        self.processor = VideoProcessor(model, conf_threshold)
        
    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            print("Cannot open video file")
            return
            
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = 0
        
        print(f"Starting analysis: {total_frames} frames, FPS: {fps}")
        
        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            processed_frame, violations = self.processor.process_frame(frame)
            
            self.frame_processed.emit(processed_frame, violations)
            
            progress = int((frame_count / total_frames) * 100)
            self.progress_updated.emit(progress)
            
            if fps > 0:
                self.msleep(max(1, int(1000 / fps)))
            else:
                self.msleep(33)
                
            if frame_count % 50 == 0:
                print(f"Processed frames: {frame_count}/{total_frames}")
        
        cap.release()
        print("Video analysis completed")
        self.analysis_finished.emit()
    
    def stop(self):
        self.is_running = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.model = None
        self.video_thread = None
        self.current_video_path = None
        self.violations_log = []
        self.is_analyzing = False
        
        self.init_ui()
        self.load_model()
        
    def init_ui(self):
        self.setWindowTitle("PPE Monitoring System v1.0")
        self.setGeometry(100, 100, 1400, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        
        splitter = QSplitter(Qt.Horizontal)
        
        video_widget = QWidget()
        video_layout = QVBoxLayout(video_widget)
        
        self.video_label = QLabel("PPE Monitoring System - Real-time Detection")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px; color: #2c3e50;")
        video_layout.addWidget(self.video_label)
        
        self.video_display = QLabel()
        self.video_display.setAlignment(Qt.AlignCenter)
        self.video_display.setMinimumSize(800, 600)
        self.video_display.setStyleSheet("border: 2px solid #bdc3c7; background-color: #2c3e50; color: white; font-size: 14pt; border-radius: 5px;")
        self.video_display.setText("Load video to start analysis")
        video_layout.addWidget(self.video_display)
        
        control_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load Video")
        self.load_btn.clicked.connect(self.load_video)
        self.load_btn.setStyleSheet("font-size: 12pt; padding: 10px; background-color: #3498db; color: white; border: none; border-radius: 5px;")
        control_layout.addWidget(self.load_btn)
        
        self.play_btn = QPushButton("Start Analysis")
        self.play_btn.clicked.connect(self.toggle_analysis)
        self.play_btn.setEnabled(False)
        self.play_btn.setStyleSheet("font-size: 12pt; padding: 10px; background-color: #27ae60; color: white; border: none; border-radius: 5px;")
        control_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self.stop_analysis)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("font-size: 12pt; padding: 10px; background-color: #e74c3c; color: white; border: none; border-radius: 5px;")
        control_layout.addWidget(self.stop_btn)
        
        video_layout.addLayout(control_layout)
        
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Confidence threshold:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(50, 95)
        self.conf_slider.setValue(65)
        self.conf_slider.valueChanged.connect(self.confidence_changed)
        settings_layout.addWidget(self.conf_slider)
        
        self.conf_label = QLabel("0.65")
        self.conf_label.setStyleSheet("font-weight: bold; color: #2c3e50; font-size: 11pt;")
        settings_layout.addWidget(self.conf_label)
        
        self.model_info = QLabel("")
        self.model_info.setStyleSheet("color: #7f8c8d; font-size: 10pt;")
        settings_layout.addWidget(self.model_info)
        
        settings_layout.addStretch()
        video_layout.addLayout(settings_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("border: 2px solid grey; border-radius: 5px; text-align: center;")
        video_layout.addWidget(self.progress_bar)
        
        log_widget = QWidget()
        log_layout = QVBoxLayout(log_widget)
        
        log_title = QLabel("Violations Log")
        log_title.setAlignment(Qt.AlignCenter)
        log_title.setStyleSheet("font-size: 14pt; font-weight: bold; margin: 10px; background-color: #34495e; color: white; padding: 12px; border-radius: 5px;")
        log_layout.addWidget(log_title)
        
        self.violations_list = QListWidget()
        self.violations_list.setStyleSheet("font-family: Consolas, monospace; font-size: 10pt; border: 2px solid #bdc3c7; border-radius: 5px; background-color: #ecf0f1;")
        log_layout.addWidget(self.violations_list)
        
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        
        self.stats_label = QLabel("Statistics: 0 violations")
        self.stats_label.setStyleSheet("font-size: 11pt; padding: 12px; background-color: #ecf0f1; border: 2px solid #bdc3c7; border-radius: 5px; color: #2c3e50;")
        stats_layout.addWidget(self.stats_label)
        
        journal_buttons_layout = QHBoxLayout()
        
        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.clicked.connect(self.clear_journal)
        self.clear_btn.setStyleSheet("padding: 8px; background-color: #e74c3c; color: white; border: none; border-radius: 5px;")
        journal_buttons_layout.addWidget(self.clear_btn)
        
        self.export_btn = QPushButton("Export to CSV")
        self.export_btn.clicked.connect(self.export_journal)
        self.export_btn.setStyleSheet("padding: 8px; background-color: #27ae60; color: white; border: none; border-radius: 5px;")
        journal_buttons_layout.addWidget(self.export_btn)
        
        stats_layout.addLayout(journal_buttons_layout)
        log_layout.addWidget(stats_widget)
        
        splitter.addWidget(video_widget)
        splitter.addWidget(log_widget)
        splitter.setSizes([800, 400])
        
        main_layout.addWidget(splitter)
        
    def load_model(self):
        try:
            model_path = get_model_path()
            
            if model_path and os.path.exists(model_path):
                self.model = YOLO(model_path)
                model_name = os.path.basename(model_path)
                self.model_info.setText(f"Model: {model_name}")
                print(f"Model loaded: {model_path}")
                print(f"Model classes: {self.model.names}")
            else:
                self.model = YOLO('yolov8n.pt')
                self.model_info.setText("Model: YOLOv8n (demo)")
                print("Using standard YOLO model (demo mode)")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Cannot load model: {e}")
            self.model = None
            
    def load_video(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", 
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv);;All Files (*)"
        )
        
        if file_path:
            self.current_video_path = file_path
            filename = os.path.basename(file_path)
            self.video_label.setText(f"Video: {filename}")
            
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            if ret:
                self.display_frame(frame)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                info_text = f"Frames: {total_frames} | FPS: {fps:.1f}"
                self.model_info.setText(f"{self.model_info.text()} | {info_text}")
            cap.release()
            
            self.play_btn.setEnabled(True)
            self.violations_list.clear()
            self.violations_log.clear()
            self.update_stats()
            
            print(f"Video loaded: {filename}")
    
    def toggle_analysis(self):
        if self.is_analyzing:
            self.stop_analysis()
        else:
            self.start_analysis()
    
    def start_analysis(self):
        if not self.current_video_path or not self.model:
            QMessageBox.warning(self, "Warning", "Please load video and model first")
            return
        
        print("Starting video analysis...")
        self.is_analyzing = True
        self.play_btn.setText("Pause")
        self.play_btn.setStyleSheet("font-size: 12pt; padding: 10px; background-color: #f39c12; color: white; border: none; border-radius: 5px;")
        self.stop_btn.setEnabled(True)
        self.load_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        self.violations_log.clear()
        self.violations_list.clear()
        self.update_stats()
        
        conf_threshold = self.conf_slider.value() / 100.0
        
        self.video_thread = VideoAnalysisThread(
            self.current_video_path,
            self.model, 
            conf_threshold
        )
        self.video_thread.frame_processed.connect(self.on_frame_processed)
        self.video_thread.analysis_finished.connect(self.on_analysis_finished)
        self.video_thread.progress_updated.connect(self.progress_bar.setValue)
        
        self.video_thread.start()
        
        print(f"Analysis started with confidence threshold: {conf_threshold}")
    
    def stop_analysis(self):
        print("Stopping analysis...")
        self.is_analyzing = False
        
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.stop()
            self.video_thread.wait()
        
        self.play_btn.setText("Continue")
        self.play_btn.setStyleSheet("font-size: 12pt; padding: 10px; background-color: #27ae60; color: white; border: none; border-radius: 5px;")
        self.stop_btn.setEnabled(False)
        self.load_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
    
    def on_frame_processed(self, processed_frame, violations):
        self.display_frame(processed_frame)
        
        for violation in violations:
            self.add_violation_to_journal(violation)
    
    def display_frame(self, frame):
        try:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            
            scaled_pixmap = pixmap.scaled(
                self.video_display.width() - 20, 
                self.video_display.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_display.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"Frame display error: {e}")
    
    def add_violation_to_journal(self, violation):
        timestamp = violation['timestamp']
        class_name = violation['class']
        confidence = violation['confidence']
        
        violation_text = f"{timestamp} | {class_name:12} | {confidence}"
        
        self.violations_list.addItem(violation_text)
        
        self.violations_list.scrollToBottom()
        
        self.violations_log.append(violation)
        self.update_stats()
    
    def update_stats(self):
        total_violations = len(self.violations_log)
        
        violation_types = {}
        for violation in self.violations_log:
            class_name = violation['class']
            violation_types[class_name] = violation_types.get(class_name, 0) + 1
        
        stats_text = f"Total violations: {total_violations}"
        for class_name, count in violation_types.items():
            stats_text += f" | {class_name}: {count}"
        
        self.stats_label.setText(stats_text)
    
    def clear_journal(self):
        self.violations_list.clear()
        self.violations_log.clear()
        self.update_stats()
        print("Log cleared")
    
    def export_journal(self):
        if not self.violations_log:
            QMessageBox.information(self, "Information", "Violations log is empty")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Violations Log", 
            f"violations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                df = pd.DataFrame(self.violations_log)
                df.to_csv(file_path, index=False, encoding='utf-8')
                QMessageBox.information(self, "Success", f"Log saved to {file_path}")
                print(f"Log exported: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot save file: {e}")
    
    def confidence_changed(self, value):
        conf_value = value / 100.0
        self.conf_label.setText(f"{conf_value:.2f}")
        
        if self.is_analyzing:
            print(f"Changing confidence threshold to: {conf_value}")
            self.stop_analysis()
            self.start_analysis()
    
    def on_analysis_finished(self):
        print("Analysis completed")
        self.stop_analysis()
        QMessageBox.information(self, "Completed", "Video analysis completed")

    def closeEvent(self, event):
        self.stop_analysis()
        event.accept()

def main():
    try:
        import cv2
        import torch
        import ultralytics
    except ImportError as e:
        print(f"Missing required libraries: {e}")
        print("Install dependencies: pip install -r requirements.txt")
        return
    
    app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()