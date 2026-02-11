import os
import time
import cv2
from PyQt5.QtCore import pyqtSignal, QThread

class VideoThread(QThread):
    frame_ready = pyqtSignal(object)
    status_update = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    finished_signal = pyqtSignal()
    error_occurred = pyqtSignal(str)

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
            if self.source_type == 'rtsp':
                print(f"[RTSP] Попытка подключения к {self.source_path}")
                self.cap = cv2.VideoCapture(self.source_path, cv2.CAP_FFMPEG)

                start_time = time.time()
                opened = False
                while time.time() - start_time < 5.0 and not opened:
                    opened = self.cap.isOpened()
                    if not opened:
                        time.sleep(0.1)
                        self.cap.open(self.source_path, cv2.CAP_FFMPEG)

                if not self.cap.isOpened():
                    error_msg = f"Не удалось открыть RTSP-поток (таймаут 5с): {self.source_path}"
                    print(f"[RTSP] {error_msg}")
                    self.error_occurred.emit(error_msg)
                    self.status_update.emit("Ошибка: RTSP-поток недоступен")
                    return

                print(f"[RTSP] Поток успешно открыт: {self.source_path}")
                self.status_update.emit(f"RTSP: {self.source_path}")

                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            elif self.source_type == 'camera':
                self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 15)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                if not self.cap.isOpened():
                    self.status_update.emit("Не удалось открыть устройство камеры")
                    self.error_occurred.emit("Камера не доступна")
                    return
                self.status_update.emit("Устройство камеры подключено")

            else:
                self.cap = cv2.VideoCapture(self.source_path)
                if not self.cap.isOpened():
                    self.status_update.emit(f"Не удалось открыть файл: {os.path.basename(self.source_path)}")
                    self.error_occurred.emit(f"Файл не найден или повреждён: {self.source_path}")
                    return

                self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
                self.status_update.emit(f"Видео загружено: {os.path.basename(self.source_path)}")

            while self.is_running:
                try:
                    ret, frame = self.cap.read()
                    if not ret:
                        if self.source_type == 'rtsp':
                            error_msg = "Потеря соединения с RTSP-потоком"
                            print(f"[RTSP] {error_msg}")
                            self.error_occurred.emit(error_msg)
                            self.status_update.emit("Ошибка: потеря RTSP")
                        else:
                            if self.source_type == 'video':
                                self.status_update.emit("Воспроизведение видео завершено")
                                self.finished_signal.emit()
                        break

                    if self.source_type == 'camera' or self.source_type == 'rtsp':
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
                    error_msg = f"Ошибка чтения кадра: {str(e)}"
                    print(f"[{self.source_type}] {error_msg}")
                    self.error_occurred.emit(error_msg)
                    self.status_update.emit("Ошибка видеопотока")
                    break

        except Exception as e:
            error_msg = f"Критическая ошибка в VideoThread: {str(e)}"
            print(f"[VideoThread] {error_msg}")
            self.error_occurred.emit(error_msg)
            self.status_update.emit("Внутренняя ошибка потока")
        finally:
            if self.cap is not None:
                self.cap.release()
            print(f"[VideoThread] Поток {self.source_type} завершён")

    def stop(self):
        self.is_running = False
        if self.cap is not None:
            self.cap.release()