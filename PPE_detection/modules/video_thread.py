import os
import time

import cv2
from PyQt5.QtCore import pyqtSignal, QThread


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
