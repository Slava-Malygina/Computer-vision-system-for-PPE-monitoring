import os
import time
import cv2
from PyQt5.QtCore import pyqtSignal, QThread


class VideoThread(QThread):
    frame_ready = pyqtSignal(object, str)
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished_signal = pyqtSignal()
    error_occurred = pyqtSignal(str, str)
    fps_updated = pyqtSignal(float)

    def __init__(self, source_type, source_path):
        super().__init__()
        self.source_type = source_type
        self.source_path = source_path
        self.is_running = False
        self.cap = None
        self.total_frames = 0
        self.current_frame = 0
        self.rtsp_reconnect_attempts = 5
        self.rtsp_reconnect_delay = 1.0

    def run(self):
        self.is_running = True
        self.frame_count = 0
        self.last_fps_time = time.time()

        try:
            if self.source_type == 'rtsp':
                self.status_update.emit("RTSP: подключение...")
                if not self.open_rtsp():
                    self.error_occurred.emit(
                        "rtsp_open_failed",
                        f"Не удалось открыть RTSP-поток: {self.source_path}"
                    )
                    return

                self.status_update.emit(f"RTSP подключён: {self.source_path}")

                print(f"[RTSP] Поток успешно открыт: {self.source_path}")
                self.status_update.emit(f"RTSP: {self.source_path}")

            elif self.source_type == 'camera':
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 15)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not self.cap.isOpened():
                    self.status_update.emit("Не удалось открыть устройство камеры")
                    self.error_occurred.emit("camera_unavailable", "Камера не доступна")
                    return
                self.status_update.emit("Устройство камеры подключено")

            else:
                self.open_rtsp()
                if not self.cap.isOpened():
                    self.status_update.emit(f"Не удалось открыть файл: {os.path.basename(self.source_path)}")
                    self.error_occurred.emit("video_open_failed", "Файл не найден или повреждён")
                    return

                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.status_update.emit(f"Видео загружено: {os.path.basename(self.source_path)}")

            while self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if not ret:
                        if self.source_type == 'rtsp':
                            self.status_update.emit("RTSP: соединение потеряно, переподключение...")
                            reconnected = False
                            for attempt in range(self.rtsp_reconnect_attempts):
                                if not self.is_running:
                                    break
                                self.status_update.emit(
                                    f"RTSP: попытка {attempt + 1}/{self.rtsp_reconnect_attempts}"
                                )
                                if self.open_rtsp():
                                    self.status_update.emit("RTSP: соединение восстановлено")
                                    reconnected = True
                                    break
                                time.sleep(self.rtsp_reconnect_delay)

                            if reconnected:
                                continue

                            self.error_occurred.emit(
                                "rtsp_lost",
                                "RTSP-поток недоступен. Переподключение не удалось."
                            )
                            break
                        if self.source_type == 'video':
                            self.status_update.emit("Воспроизведение видео завершено")
                            self.finished_signal.emit()
                            break

                        self.error_occurred.emit(
                            "camera_lost",
                            "Потеря соединения с камерой"
                        )
                        break


                    self.frame_count += 1
                    current_time = time.time()
                    if current_time - self.last_fps_time >= 1.0:
                        self.current_fps = self.frame_count / (current_time - self.last_fps_time)
                        self.fps_updated.emit(self.current_fps)
                        self.frame_count = 0
                        self.last_fps_time = current_time

                    if self.source_type in ('camera', 'rtsp'):
                        small_frame = frame
                    else:
                        small_frame = cv2.resize(frame, (640, 480))
                    self.frame_ready.emit(small_frame, self.source_path)

                    if self.source_type == 'video':
                        self.current_frame += 1
                        progress = int((self.current_frame / self.total_frames) * 100)
                        self.progress_update.emit(progress)

                    time.sleep(0.033)

                except Exception as e:
                    self.error_occurred.emit(
                        "frame_read_error",
                        f"Ошибка чтения кадра: {str(e)}"
                    )
                    break

        except Exception as e:
            error_msg = f"Критическая ошибка в VideoThread: {str(e)}"
            print(f"[VideoThread] {error_msg}")
            self.error_occurred.emit(
                "internal_error",
                f"Критическая ошибка VideoThread: {str(e)}"
            )
            self.status_update.emit("Внутренняя ошибка потока")
        finally:
            if self.cap is not None:
                self.cap.release()
            print(f"[VideoThread] Поток {self.source_type} завершён")

    def stop(self):
        self.is_running = False

    def open_rtsp(self, timeout: float = 5.0) -> bool:
        if self.cap is not None:
            self.cap.release()
            self.cap = None

        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.is_running:
                return False
            cap = cv2.VideoCapture(self.source_path, cv2.CAP_FFMPEG)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.cap = cap
                return True
            cap.release()
            time.sleep(0.3)
        return False

