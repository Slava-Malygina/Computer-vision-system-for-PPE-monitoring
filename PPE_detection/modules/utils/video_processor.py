import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from modules.violation_detector import ViolationDetector


class VideoProcessor(QObject):
    frame_ready = pyqtSignal(int, np.ndarray)
    detection_done = pyqtSignal(int, list, np.ndarray)
    status_changed = pyqtSignal(str)
    fps_updated = pyqtSignal(int, float)
    camera_status = pyqtSignal(int, str)

    def __init__(self, logger, camera_manager, frame_counter):
        super().__init__()
        self.logger = logger
        self.model = None
        self.is_detecting = False
        self.conf_threshold = 0.5
        self.detection_interval = 1

        self.single_thread = None
        self.camera_manager = camera_manager

        self.camera_frames = {}
        self.camera_display_frames = {}
        self.detection_in_progress = {}
        self.last_detection_time = {}
        self.camera_index_map = {}
        self.rtsp_addresses = []

        self.violation_detector = ViolationDetector()

        self.current_frame = None
        self.frame_counter = frame_counter
        self.processing_frame = False
        self.last_detections = []
        self.last_tracks = []
        self.last_violations = {}

    def set_conf_threshold(self, value):
        self.conf_threshold = value

    def create_detection_thread(self, frame, source_id, camera_index=None, class_thresholds=None):
        from detection_thread import DetectionThread
        thread = DetectionThread(
            self.model,
            frame,
            self.conf_threshold,
            self.frame_counter,
            source_id,
            class_thresholds
        )
        return thread

    def increment_frame_counter(self):
        self.frame_counter += 1

    def load_model(self):
        from model_loader import ModelLoader

        try:
            loader = ModelLoader()
            self.model = loader.load()
            if self.model:
                print(f"Модель загружена: {loader.model_name}")
                return True
            return False
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
            self.model = None
            return False
