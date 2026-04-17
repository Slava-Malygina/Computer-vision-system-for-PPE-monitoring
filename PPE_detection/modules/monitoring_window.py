import os
import time
import cv2
from datetime import datetime

from PyQt5.QtCore import QTimer, Qt, QEvent
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QSizePolicy, QFrame
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QLabel, QPushButton, QListWidget, QSlider, QMessageBox, \
    QSplitter, QComboBox, QFileDialog, QProgressBar, QGroupBox, QLineEdit

from modules.UI.AspectRatioLabel import AspectRatioLabel, ResizeWatcher
from modules.UI.gradient_outline_button import GradientOutlineButton
from modules.UI.multi_camera_widget import MultiCameraWidget
from modules.UI.rtsp_config_dialog import RtspConfigDialog
from modules.UI.video_errors import show_error, show_rtsp_error
from modules.camera_manager import CameraManager
from modules.utils.style_loader import StyleLoader
from modules.utils.threshold_manager import ThresholdManager
from modules.utils.tracking_utils import TrackingManager, draw_detections_on_frame_with_tracking, \
    draw_detections_on_frame
from modules.utils.ui_handler import UIHandler
from modules.utils.video_processor import VideoProcessor
from modules.video_thread import VideoThread
from modules.violation_detector import ViolationDetector
from modules.utils.screenshot_saver import save_violation_screenshot
from modules.utils.cleanup_manager import cleanup_manager

class MonitoringTab(QWidget):

    def __init__(self, logger, main_window):
        super().__init__()
        self.main_window = main_window
        self.single_video_thread = None
        self.detection_thread = None
        self._is_video_running = False
        self.detection_threads = []
        self.current_frame = None
        self.frame_counter = 0
        self.thresholdManager = ThresholdManager()
        self.threshold_manager = ThresholdManager()
        self.tracking_manager = TrackingManager()
        self.camera_manager = CameraManager()
        self.video_processor = VideoProcessor(logger, self.camera_manager, self.frame_counter)

        self.available_cameras = []
        self.violation_detector = ViolationDetector()
        self.violation_logger = logger

        self.processing_frame = False
        self.last_detection_time = 0
        self.detection_interval = 1
        self.next_track_id = 0
        self.last_detections = []
        self.last_tracks = []
        self.last_violations = {}
        self.current_video_path = None

        self.multi_camera_mode = False
        self.camera_detection_in_progress = {}

        self.camera_fps = {}
        self.camera_status = {}
        self.camera_last_detections = {}
        self.camera_last_tracks = {}
        self.camera_last_violations = {}
        self.camera_last_frame = {}
        self.camera_last_displayed_frame = {}
        self.camera_last_detection_time = {}
        self.camera_tracking_managers = {}


        self.camera_original_frames = {}
        self.camera_displayed_frames = {}

        # Полноэкранный режим
        self.fullscreen_mode = False
        self.fullscreen_camera_index = None

        self.init_ui()

        if self.video_processor.load_model():
            self.model_label.setText("Модель: загружена")
        self.detect_cameras()
        self.setup_timers()
        self.rtsp_addresses = [""] * RtspConfigDialog.MAX_SOURCES

        self.camera_index_map = {}
        self.ui_handler = UIHandler(
            self.multi_camera_widget,
            self.single_video_label,
            self.violations_list,
            self.status_label,
            self.stats_label,
            self.conf_label
        )
        self.set_addr_auto()
        self.multi_camera_widget.camera_clicked.connect(self.enter_fullscreen)

        self.threshold_manager.thresholds_updated.connect(self.on_thresholds_updated)
        deleted = cleanup_manager.cleanup_old_screenshots(days=30)
        if deleted > 0:
            print(f"[Очистка] Удалено {deleted} старых скриншотов")

    def init_ui(self):
        monitor_layout = QVBoxLayout(self)
        monitor_layout.setContentsMargins(0, 0, 0, 0)
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(2, 2, 2, 2)
        header_layout.addStretch()
        stats_widget = QWidget()
        stats_layout = QHBoxLayout(stats_widget)

        self.stats_label = QLabel("Нарушения: 0")
        self.stats_label.setObjectName("statsLabel")

        stats_layout.addWidget(self.stats_label)
        header_layout.addWidget(stats_widget)

        content_layout = QHBoxLayout()

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        spacer = QWidget()
        spacer.setFixedWidth(20)
        spacer.setStyleSheet("background-color: transparent;")
        left_layout.addWidget(spacer)
        video_group = ResizeWatcher()
        video_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout = QVBoxLayout(video_group)
        video_layout.setContentsMargins(0, 0, 0, 0)

        self.multi_cam_container = QWidget()
        self.multi_cam_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        multi_cam_layout = QVBoxLayout(self.multi_cam_container)
        multi_cam_layout.setContentsMargins(0, 0, 0, 0)
        multi_cam_layout.setAlignment(Qt.AlignCenter)


        self.video_container = QWidget()
        self.video_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(self.video_container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setAlignment(Qt.AlignCenter)

        self.single_video_label = AspectRatioLabel(aspect_ratio=16/9)
        self.single_video_label.setText("Выберите источник видеопотока")
        container_layout.addWidget(self.single_video_label)

        video_layout.addWidget(self.video_container, stretch=1)
        self.multi_cam_container.setVisible(False)
        self.multi_camera_widget = MultiCameraWidget()
        self.multi_camera_widget.setVisible(False)
        multi_cam_layout.addWidget(self.multi_camera_widget)
        video_layout.addWidget(self.multi_cam_container, stretch=1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        video_layout.addWidget(self.progress_bar)

        left_layout.addWidget(video_group, stretch=1)

        control_group = QWidget()
        control_layout = QVBoxLayout(control_group)

        source_layout = QHBoxLayout()
        source_layout.addWidget(QLabel("Источник:"))

        self.source_combo = QComboBox()
        combo_box_stylesheet = StyleLoader.load_stylesheet("combo_box_general_style.qss")
        self.source_combo.setStyleSheet(combo_box_stylesheet)

        self.source_combo.addItem("Камера", "camera")
        self.source_combo.addItem("Видеофайл", "video")
        self.source_combo.addItem("IP-камера", "rtsp")
        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        source_layout.addWidget(self.source_combo)

        self.camera_combo = QComboBox()
        self.camera_combo.setMinimumWidth(120)
        self.camera_combo.setStyleSheet(combo_box_stylesheet)
        source_layout.addWidget(self.camera_combo)

        self.video_path_label = QLabel("Файл не выбран")
        source_layout.addWidget(self.video_path_label)

        self.rtsp_input = QLineEdit()
        self.rtsp_input.setPlaceholderText("Введите RTSP URL (rtsp://...)")
        self.rtsp_input.setVisible(False)
        self.rtsp_input.setStyleSheet("""
            QLineEdit {
                background: #323055;
                border: 1px solid #3a424e;
                border-radius: 10px;
                padding: 4px;
                color: white;
            }
        """)
        self.rtsp_input.textChanged.connect(self.on_rtsp_text_changed)
        source_layout.addWidget(self.rtsp_input)

        self.add_rtsp_btn = QPushButton("Настройки")
        self.add_rtsp_btn.setVisible(False)
        self.add_rtsp_btn.clicked.connect(self._open_rtsp_config)
        source_layout.addWidget(self.add_rtsp_btn)

        self.browse_btn = QPushButton("Выбрать...")
        self.browse_btn.clicked.connect(self.browse_video_file)
        source_layout.addWidget(self.browse_btn)

        source_layout.addStretch()
        control_layout.addLayout(source_layout)

        buttons_layout = QHBoxLayout()
        self.video_btn = QPushButton("Запуск видео")
        self.video_btn.setMinimumHeight(40)
        self.video_btn.clicked.connect(self.on_video_btn_clicked)



        control_layout.addLayout(buttons_layout)
        left_layout.addWidget(control_group, stretch=0)

        self.detection_btn = QPushButton("Запуск распознавания")
        self.detection_btn.setMinimumHeight(35)
        self.detection_btn.clicked.connect(self.on_detection_btn_clicked)
        self.detection_btn.setEnabled(False)


        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Порог уверенности:"))
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(20, 95)
        self.conf_slider.setValue(50)
        self.conf_slider.valueChanged.connect(self.on_confidence_changed)
        confidence_layout.addWidget(self.conf_slider)
        self.conf_label = QLabel("0.50")
        self.conf_label.setMinimumWidth(40)
        confidence_layout.addWidget(self.conf_label)

        self.confidence_widget = QWidget()
        self.confidence_widget.setLayout(confidence_layout)
        self.detection_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        buttons_layout.addWidget(self.video_btn, stretch=1)
        buttons_layout.addWidget(self.detection_btn, stretch=1)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.confidence_widget, stretch=2)

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
        right_panel.setObjectName("rightPanel")
        up_btn_layout = QHBoxLayout()

        switch_tap_btn = GradientOutlineButton(
            "Журнал",
            left_icon_path="../../resources/icons/ic_camera.png",
            right_icon_path="../../resources/icons/ic_arrow.png"
        )
        switch_tap_btn.clicked_callback = self.on_switch_btn_click
        up_btn_layout.addWidget(switch_tap_btn)
        up_btn_layout.setAlignment(switch_tap_btn, Qt.AlignRight)

        right_layout.addLayout(up_btn_layout)

        violations_group = QWidget()
        self.violations_label = QLabel("Последние нарушения")
        self.violations_label.setObjectName("funcLabel")

        line = QFrame()
        line.setObjectName("line")
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)

        line_bottom = QFrame()
        line_bottom.setObjectName("line")
        line_bottom.setFrameShape(QFrame.HLine)
        line_bottom.setFrameShadow(QFrame.Sunken)

        violations_layout = QVBoxLayout(violations_group)
        self.violations_list = QListWidget()
        self.violations_list.setWordWrap(True)
        self.violations_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


        violations_layout.addWidget(self.violations_label)
        violations_layout.addSpacing(40)
        violations_layout.addWidget(line)
        violations_layout.addSpacing(20)
        violations_layout.addWidget(self.violations_list)
        violations_layout.addSpacing(20)
        violations_layout.addWidget(line_bottom)
        violations_layout.addSpacing(40)

        log_buttons_layout = QHBoxLayout()
        log_buttons_layout.addStretch()
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.setFixedWidth(100)
        self.clear_btn.clicked.connect(self.clear_journal)
        log_buttons_layout.addWidget(self.clear_btn)
        log_buttons_layout.addStretch()

        violations_layout.addLayout(log_buttons_layout)
        right_layout.addWidget(violations_group)
        right_layout.addWidget(header_widget)

        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel)
        content_layout.setStretch(0, 8)
        content_layout.setStretch(1, 2)

        monitor_layout.addLayout(content_layout)

        self.source_combo.currentIndexChanged.connect(self.on_source_changed)
        self.on_source_changed(0)
        self.left_panel = left_panel
        self.right_panel = right_panel
        self.control_group = control_group
        self.info_widget = info_widget
        self.header_widget = header_widget

    @property
    def is_video_running(self):
        return self._is_video_running

    @is_video_running.setter
    def is_video_running(self, value):
        self._is_video_running = value
        if not value:
            self.video_btn.setText("Запуск видео")
        else:
            self.video_btn.setText("Остановка видео")

    def on_switch_btn_click(self):
        self.main_window.setCurrentIndex(1)

    def set_addr_auto(self):
        result = self.thresholdManager.get_first_4_rtsp_urls()
        self.rtsp_addresses = [addr for addr in result if addr]
        self.multi_camera_widget.set_addresses(self.rtsp_addresses)

    def on_source_changed(self, index):
        source_type = self.source_combo.currentData()
        self.camera_combo.setVisible(False)
        self.video_path_label.setVisible(False)
        self.browse_btn.setVisible(False)
        self.rtsp_input.setVisible(False)
        self.add_rtsp_btn.setVisible(False)
        if self.is_video_running:
            self.stop_video()
        if source_type == 'camera':
            self.camera_combo.setVisible(True)
            self.multi_camera_widget.setVisible(False)
            self.multi_cam_container.setVisible(False)
            self.video_container.setVisible(True)
            self.single_video_label.setVisible(True)
            self.confidence_widget.setVisible(True)
        elif source_type == 'video':
            self.video_path_label.setVisible(True)
            self.browse_btn.setVisible(True)
            self.multi_cam_container.setVisible(False)
            self.multi_camera_widget.setVisible(False)
            self.video_container.setVisible(True)
            self.single_video_label.setVisible(True)
            self.confidence_widget.setVisible(True)
        elif source_type == 'rtsp':
            self.rtsp_input.setVisible(True)
            self.add_rtsp_btn.setVisible(True)
            self.multi_cam_container.setVisible(True)
            self.single_video_label.setVisible(False)
            self.video_container.setVisible(False)
            self.multi_camera_widget.set_max_width(1400)
            self.multi_camera_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

            active_count = len([a for a in self.rtsp_addresses if a])
            if active_count > 0:
                self.multi_camera_widget.setVisible(True)
                self.multi_camera_widget.set_camera_count(active_count)
            else:
                self.multi_camera_widget.setVisible(False)
            self.confidence_widget.setVisible(False)
        self.rtsp_input.setStyleSheet("""
             QLineEdit {
                background: #323055;
                border: 1px solid #3a424e;
                border-radius: 10px;
                padding: 4px;
                color: white;
            }

        """)

    def check_rtsp_url(self) -> bool:
        if self.source_combo.currentData() == "rtsp":
            url = self.rtsp_input.text().strip()
            return url == "" or url.startswith("rtsp://")
        return True

    def on_rtsp_text_changed(self):
        if self.check_rtsp_url():
            self.rtsp_input.setStyleSheet("""
            QLineEdit {
                background: #323055;
                border: 1px solid #3a424e;
                border-radius: 10px;
                padding: 4px;
                color: white;
            }
            """)
        else:
            self.rtsp_input.setStyleSheet("""
                QLineEdit {
                    background: #323055;
                    border: 2px solid red;
                    border-radius: 4px;
                    padding: 4px;
                    color: white;
                }
            """)

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

    def on_video_btn_clicked(self):
        if hasattr(self, '_video_btn_locked') and self._video_btn_locked:

            return

        self._video_btn_locked = True

        self._original_video_btn_style = self.video_btn.styleSheet()

        self.video_btn.setStyleSheet("""
            QPushButton {
                color: #adb5bd;
            }
        """)
        try:
            if not self.is_video_running:
                self.start_video()
            else:
                self.stop_video()
        finally:

            QTimer.singleShot(5000, lambda: self._restore_btn())

    def _restore_btn(self):
        self._video_btn_locked = False
        self.video_btn.setStyleSheet("")



    def start_video(self):
        source_type = self.source_combo.currentData()

        if source_type == 'camera':
            self._start_single_video(source_type, "camera")

        elif source_type == 'video':
            if not hasattr(self, 'current_video_path') or not self.current_video_path:
                QMessageBox.warning(self, "Warning", "Выберите видеофайл!")
                return
            self._start_single_video(source_type, self.current_video_path)

        elif source_type == 'rtsp':
            active_addresses = [addr for addr in self.rtsp_addresses if addr]

            if not active_addresses:
                QMessageBox.warning(self, "Warning", "Нет настроенных RTSP-камер. Добавьте адреса.")
                return
            self._sync_cameras_with_addresses(active_addresses)
            self.multi_camera_mode = True
            self.multi_camera_widget.setVisible(True)
            self.multi_camera_widget.set_camera_count(len(active_addresses))
            self.single_video_label.setVisible(False)
            self.progress_bar.setVisible(False)

            self.camera_last_frame.clear()
            self.camera_last_displayed_frame.clear()
            self.camera_last_detections.clear()
            self.camera_manager.start_all()
        self.is_video_running = True

        self.detection_btn.setEnabled(True)

        self.display_timer.start(67)

    def stop_video(self):

        self.stop_detection()

        if self.single_video_thread and self.single_video_thread.isRunning():
            self.single_video_thread.stop()
            self.single_video_thread.wait(2000)
            self.single_video_thread = None

        self.camera_manager.stop_all()
        for thread in self.camera_manager._cameras:
            if thread.isRunning():
                thread.wait(2000)

        self._clear_camera_state()
        self.clear_detection_state()
        self.current_frame = None
        self.last_detections.clear()
        self.last_tracks.clear()
        self.last_violations.clear()

        self.single_video_label.clear()
        self.single_video_label.setText("\n\nВыберите источник видеопотока")
        self.multi_camera_widget.clear_all()
        self.multi_camera_widget.setVisible(False)

        self.display_timer.stop()

        self.is_video_running = False
        self.detection_btn.setEnabled(False)
        self.ui_handler.update_status("")
        self.fps_label.setText("FPS: 0")
        self.exit_fullscreen()
        self.camera_index_map.clear()

    def on_video_finished(self):
        self.stop_video()
        self.ui_handler.update_status("Завершено")

    def on_single_video_error(self, error_code: str, message: str):
        self.ui_handler.update_status(f"Ошибка: {message}")
        if error_code in ("rtsp_lost", "rtsp_open_failed"):
            self.handle_rtsp_loss()
            return
        show_error(self, error_code, message)
        self.stop_video()

    def on_detection_btn_clicked(self):
        if self.video_processor.is_detecting:
            self.stop_detection()
        else:
            self.start_detection()

    def start_detection(self):
        if not self.video_processor.model:
            QMessageBox.warning(self, "Warning", "Model not loaded!")
            return

        self.video_processor.is_detecting = True
        self.ui_handler.update_status("В процессе")
        self.detection_btn.setText("Остановка распознавания")


    def stop_detection(self):
        self.video_processor.is_detecting = False
        self._stop_detection_threads()
        self.detection_btn.setText("Запуск распознавания")
        self.ui_handler.update_status("Остановлено")
        self.detection_btn.setEnabled(True)
        self.clear_detection_state()

        self.last_detections.clear()
        self.last_tracks.clear()
        self.last_violations.clear()
        if not self.multi_camera_mode and self.single_video_label:
            if self.current_frame is not None:
                self.ui_handler.update_single_frame(self.current_frame)
            else:
                self.single_video_label.clear()
                self.single_video_label.setText("\n\nВыберите источник видеопотока")
        else:
            for idx, frame in self.camera_original_frames.items():
                if frame is not None:
                    self.ui_handler.update_frame(idx, frame)

    def on_frame_received(self, frame, source_id):
        self.current_frame = frame

        if self.video_processor.is_detecting and self.video_processor.model is not None and not self.processing_frame:
            current_time = time.time()
            if current_time - self.last_detection_time >= self.detection_interval:
                self.last_detection_time = current_time
                self.processing_frame = True

                self.detection_thread = self._create_detection_thread(frame, source_id)
                self.detection_thread.start()
                self.detection_threads.append(self.detection_thread)


    def on_detection_done(self, detections, frame, frame_counter, results, source_id):
        try:
            violations = []
            tracks = self.tracking_manager.update(detections)
            result = self.violation_detector.process_frame(
                detections, tracks, frame_counter
            )
            self.last_violations = result['violations_dict']
            self.last_detections = detections
            self.last_tracks = tracks

            screenshot_path = None
            if result['violations_dict']:
                screenshot_path = save_violation_screenshot(
                    frame, detections, tracks, result['violations_dict'],
                    frame_counter, source_id
                )

            self.video_processor.increment_frame_counter()
            for human_id, human_violations in result['violations_dict'].items():
                for violation in human_violations:
                    violation_data = {
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'class': violation['violation_type'],
                        'confidence': violation['confidence'],
                        'human_id': human_id,
                        'camera_id': source_id
                    }
                    violations.append(violation_data)
                    self.violation_logger.add_frame_violations(
                        frame_counter,
                        {human_id: [violation]},
                        source_id,
                        screenshot_path
                    )

            for violation in violations:
                self.ui_handler.add_violation(violation)

        except Exception as e:
            print(f"Detection processing error: {e}")
        finally:
            self.processing_frame = False

    def on_camera_frame(self, camera_index, frame, source_id):
        self.camera_original_frames[camera_index] = frame

        last_detections = self.camera_last_detections.get(camera_index)
        last_tracks = self.camera_last_tracks.get(camera_index)
        if last_detections is not None:
            display_frame = frame.copy()
            display_frame = draw_detections_on_frame_with_tracking(display_frame, last_detections, last_tracks, {})
        else:
            display_frame = frame
        self.ui_handler.update_frame(camera_index, display_frame)

        if self.fullscreen_mode and camera_index == self.fullscreen_camera_index:
            self.display_single_frame(display_frame)

        if self.video_processor.is_detecting and self.video_processor.model is not None:
            if self.camera_detection_in_progress.get(camera_index, False):
                return

            current_time = time.time()
            last_time = self.camera_last_detection_time.get(camera_index, 0)
            if current_time - last_time >= self.detection_interval:
                self.camera_last_detection_time[camera_index] = current_time
                self.camera_detection_in_progress[camera_index] = True
                detection_thread = self._create_detection_thread(frame, source_id, camera_index)
                detection_thread.finished.connect(
                    lambda idx=camera_index: self._on_detection_thread_finished(idx))
                self.detection_threads.append(detection_thread)
                detection_thread.start()

    def _on_detection_thread_finished(self, camera_index):
        self.camera_detection_in_progress[camera_index] = False

    def _remove_detection_thread(self, thread):
        if thread in self.detection_threads:
            self.detection_threads.remove(thread)

    def on_camera_detection_done(self, camera_index, detections, frame, frame_counter, results, source_id=None):
        if camera_index not in self.camera_detection_in_progress:
            return

        try:
            self.camera_last_detections[camera_index] = detections

            display_frame = frame.copy()
            draw_detections_on_frame(display_frame, detections)
            self.ui_handler.update_frame(camera_index, display_frame)

            if self.fullscreen_mode and camera_index == self.fullscreen_camera_index:
                self.display_single_frame(display_frame)

            tracker = self.camera_tracking_managers.get(camera_index)
            if tracker is None:
                from modules.utils.tracking_utils import TrackingManager
                tracker = TrackingManager()
                self.camera_tracking_managers[camera_index] = tracker
            tracks = tracker.update(detections)
            self.camera_last_tracks[camera_index] = tracks
            result = self.violation_detector.process_frame(detections, tracks, frame_counter)


            screenshot_path = None
            if result['violations_dict']:
                screenshot_path = save_violation_screenshot(
                    frame, detections, tracks, result['violations_dict'],
                    frame_counter, source_id
                )
            display_frame = draw_detections_on_frame_with_tracking(display_frame, detections, tracks, result)
            self.ui_handler.update_frame(camera_index, display_frame)
            for human_id, human_violations in result['violations_dict'].items():
                for violation in human_violations:
                    self.ui_handler.add_violation({
                        'timestamp': datetime.now().strftime("%H:%M:%S"),
                        'class': violation['violation_type'],
                        'confidence': violation['confidence'],
                        'human_id': human_id,
                        'camera_id': source_id or f"cam_{camera_index}"
                    })
                    self.violation_logger.add_frame_violations(
                        frame_counter,
                        {human_id: [violation]},
                        source_id or f"cam_{camera_index}",
                        screenshot_path
                    )
        except Exception as e:
            print(f"Multi-camera detection error for camera {camera_index}: {e}")
        finally:
            self.camera_detection_in_progress[camera_index] = False


    def on_camera_status(self, camera_index, status):
        self.camera_status[camera_index] = status
        fps = self.camera_fps.get(camera_index)

    def on_camera_fps(self, camera_index, fps):
        self.camera_fps[camera_index] = fps
        self.ui_handler.update_fps(camera_index, fps)

    def update_display(self):
        self.fps_counter += 1
        current_time = time.time()
        if current_time - self.last_fps_time >= 1.0:
            self.fps_label.setText(f"FPS: {self.fps_counter}")
            self.fps_counter = 0
            self.last_fps_time = current_time

        if self.current_frame is not None and not self.multi_camera_mode:
            display_frame = self.current_frame.copy()

            if hasattr(self, 'last_detections') and hasattr(self, 'last_tracks'):
                display_frame = draw_detections_on_frame_with_tracking(
                    display_frame,
                    self.last_detections,
                    self.last_tracks,
                    self.last_violations
                )

            self.ui_handler.update_single_frame(display_frame)


    def clear_journal(self):
        self.ui_handler.clear_journal()
        self.violation_detector.clear_recorded_violations()
        self.last_violations.clear()
        self.tracking_manager.clear()

    def on_confidence_changed(self, value):
        conf_value = value / 100.0
        self.video_processor.set_conf_threshold(conf_value)
        self.ui_handler.update_confidence_label(conf_value)

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


    def handle_rtsp_loss(self):
        action = show_rtsp_error(self, "rtsp_lost")
        if action == "retry":
            if self.video_thread.open_rtsp():
                self.status_update.emit("RTSP: переподключение успешно")
                return True
            else:
                self.status_update.emit("RTSP: повторное подключение не удалось")
                return False
        else:
            self.stop_video()
            return False

    def _open_rtsp_config(self):

        result = RtspConfigDialog.open_and_get(
            self,
            existing=self.rtsp_addresses,
            validator=None
        )
        if result is not None:
            self.stop_video()
            self.rtsp_addresses = result.copy()
        self.rtsp_input.setFocus()

    def _sync_cameras_with_addresses(self, new_addresses: list):

        if self.is_video_running:
            self.stop_video()
        for manager_idx in self.camera_index_map.values():
            try:
                self.camera_manager.get_frame_ready_signal(manager_idx).disconnect()
                self.camera_manager.get_status_signal(manager_idx).disconnect()
                fps_signal = self.camera_manager.get_fps_signal(manager_idx)
                if fps_signal:
                    fps_signal.disconnect()
            except:
                pass
            self.camera_manager.remove_camera(manager_idx)

        active_addresses = [addr for addr in new_addresses if addr]
        self.camera_index_map.clear()

        test_videos = ["test1.mp4", "test2.mp4", "test3.mp4", "test4.mp4"]

        for ui_idx, addr in enumerate(active_addresses):
            if ui_idx < len(test_videos):

                manager_idx = self.camera_manager.add_camera("rtsp", addr)

            self.camera_index_map[ui_idx] = manager_idx
            print(f"Synced: ui_idx={ui_idx}, manager_idx={manager_idx}, addr={addr}")

            self.camera_manager.get_frame_ready_signal(manager_idx).connect(
                lambda frame, source_path, idx=ui_idx: self.on_camera_frame(idx, frame, source_path)
            )
            self.camera_manager.get_status_signal(manager_idx).connect(
                lambda status, idx=ui_idx: self.on_camera_status(idx, status)
            )

            fps_signal = self.camera_manager.get_fps_signal(manager_idx)
            if fps_signal:
                fps_signal.connect(lambda fps, idx=ui_idx: self.on_camera_fps(idx, fps))

            # if not self.is_video_running:
            #     self.camera_manager.start_camera(manager_idx)

        self.rtsp_addresses = new_addresses.copy()
        self.multi_camera_widget.set_addresses(new_addresses)

        if active_addresses:
            self.multi_camera_widget.set_camera_count(len(active_addresses))
        else:
            self.multi_camera_widget.setVisible(False)

    def _create_detection_thread(self, frame, source_id, camera_index=None):
        thresholds = self.threshold_manager.get_thresholds(source_id)
        thread = self.video_processor.create_detection_thread(
            frame, source_id, camera_index, thresholds
        )
        if camera_index is not None:
            thread.detection_done.connect(
                lambda det, frm, cnt, res, src_id, idx=camera_index:
                self.on_camera_detection_done(idx, det, frm, cnt, res, src_id)
            )
        else:
            thread.detection_done.connect(self.on_detection_done)
        return thread

    def _clear_camera_state(self):

        self.camera_last_detection_time.clear()
        self.camera_original_frames.clear()
        self.camera_displayed_frames.clear()
        self.camera_last_frame.clear()
        self.camera_last_displayed_frame.clear()
        self.camera_last_detections.clear()
        self.camera_tracking_managers.clear()
        self.multi_camera_widget.clear_all()

    def clear_detection_state(self):
        self.camera_detection_in_progress.clear()
        self.last_detections.clear()
        self.last_tracks.clear()
        self.last_violations.clear()
        self.camera_last_detections.clear()
        self.camera_tracking_managers.clear()



    def _start_single_video(self, source_type, source_path):
        self.single_video_thread = VideoThread(source_type, source_path)
        self.single_video_thread.frame_ready.connect(self.on_frame_received)
        self.single_video_thread.status_update.connect(self.ui_handler.update_status)
        self.single_video_thread.progress_update.connect(self.progress_bar.setValue)
        self.single_video_thread.finished_signal.connect(self.on_video_finished)
        self.single_video_thread.error_occurred.connect(self.on_single_video_error)
        self.single_video_thread.start()

        self.progress_bar.setVisible(source_type == 'video')
        self.single_video_label.setVisible(True)
        self.multi_camera_widget.setVisible(False)

    def _stop_detection_threads(self):
        for thread in self.detection_threads:
            if thread.isRunning():
                thread.wait(1000)
        self.detection_threads.clear()

        if self.detection_thread and self.detection_thread.isRunning():
            self.detection_thread.wait(1000)

    def on_thresholds_updated(self, rtsp_url: str, new_thresholds: dict):
        for thread in self.detection_threads:
            if hasattr(thread, 'source_id') and thread.source_id == rtsp_url:
                thread.update_thresholds(new_thresholds)

    def enter_fullscreen(self, camera_index):
        if self.fullscreen_mode or not self.multi_camera_mode:
            return
        self.fullscreen_mode = True
        self.fullscreen_camera_index = camera_index

        self.multi_camera_widget.setVisible(False)
        self.multi_cam_container.setVisible(False)
        self.single_video_label.setVisible(True)
        self.video_container.setVisible(True)
        self.single_video_label.setMinimumSize(0, 0)
        self.single_video_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if camera_index in self.camera_displayed_frames:
            self.display_single_frame(self.camera_displayed_frames[camera_index])
        elif camera_index in self.camera_original_frames:
            self.display_single_frame(self.camera_original_frames[camera_index])
        else:
            self.single_video_label.setText("Ожидание кадра...")

        self.installEventFilter(self)

    def exit_fullscreen(self):
        if not self.fullscreen_mode:
            return
        self.fullscreen_mode = False
        self.fullscreen_camera_index = None
        self.multi_camera_widget.setVisible(True)
        self.multi_cam_container.setVisible(True)
        self.single_video_label.setVisible(False)
        self.video_container.setVisible(False)
        self.single_video_label.setMinimumSize(700, 500)
        self.removeEventFilter(self)

    def display_single_frame(self, frame):
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

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape and self.fullscreen_mode:
            self.exit_fullscreen()
            return True
        return super().eventFilter(obj, event)
