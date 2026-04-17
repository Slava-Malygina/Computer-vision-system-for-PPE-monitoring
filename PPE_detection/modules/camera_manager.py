from PyQt5.QtCore import QObject, pyqtSignal

from modules.video_thread import VideoThread


class CameraManager(QObject):
    camera_added = pyqtSignal(int)
    camera_removed = pyqtSignal(int)
    camera_started = pyqtSignal(int)
    camera_stopped = pyqtSignal(int)
    camera_error = pyqtSignal(int, str)
    camera_fps = pyqtSignal(int, float)

    def __init__(self):
        super().__init__()
        self._cameras = []
        self._active_indices = set()

    def add_camera(self, source_type, source_path):
        thread = VideoThread(source_type, source_path)
        thread.error_occurred.connect(
            lambda msg, idx=len(self._cameras): self._on_error(idx, msg)
        )
        thread.fps_updated.connect(
            lambda fps, idx=len(self._cameras): self.camera_fps.emit(idx, fps)
        )
        self._cameras.append(thread)
        index = len(self._cameras) - 1
        self.camera_added.emit(index)
        return index

    def get_fps_signal(self, index):
        if 0 <= index < len(self._cameras):
            return self._cameras[index].fps_updated
        return None
    def remove_camera(self, index):
        if 0 <= index < len(self._cameras):
            self.stop_camera(index)
            thread = self._cameras[index]
            thread.wait()
            thread.deleteLater()
            del self._cameras[index]
            self.camera_removed.emit(index)

    def start_camera(self, index):
        if 0 <= index < len(self._cameras) and index not in self._active_indices:
            thread = self._cameras[index]
            thread.start()
            self._active_indices.add(index)
            self.camera_started.emit(index)

    def stop_camera(self, index):
        if 0 <= index < len(self._cameras) and index in self._active_indices:
            thread = self._cameras[index]
            thread.stop()
            self._active_indices.discard(index)
            self.camera_stopped.emit(index)

    def start_all(self):
        print("Всего камер",len(self._cameras) )
        for i in range(len(self._cameras)):
            self.start_camera(i)

    def stop_all(self):
        for i in list(self._active_indices):
            self.stop_camera(i)

    def stop_all_and_wait(self, timeout_ms=2000):
        for i in list(self._active_indices):
            self.stop_camera(i)
        for thread in self._cameras:
            if thread.isRunning():
                thread.wait(timeout_ms)

    def _on_error(self, index, message):
        self.camera_error.emit(index, message)
        self.stop_camera(index)

    def get_frame_ready_signal(self, index):
        if 0 <= index < len(self._cameras):
            return self._cameras[index].frame_ready
        return None

    def get_status_signal(self, index):
        if 0 <= index < len(self._cameras):
            return self._cameras[index].status_update
        return None

    def camera_count(self):
        return len(self._cameras)

    def is_active(self, index):
        return index in self._active_indices

    def clear(self):

        self.stop_all()

        for i, thread in enumerate(self._cameras):
            if thread.isRunning():
                thread.stop()
                if not thread.wait(3000):  #
                    print(f": Thread {i} не остановлен во время")
                    thread.terminate()
                    thread.wait(500)

        for thread in self._cameras:
            try:
                thread.frame_ready.disconnect()
                thread.status_update.disconnect()
                thread.fps_updated.disconnect()
                thread.error_occurred.disconnect()
            except:
                pass

        for thread in self._cameras:
            thread.deleteLater()

        self._cameras.clear()
        self._active_indices.clear()
        print(
            f"[CameraManager] Полная очистка завершена. Камер: {len(self._cameras)}, Активных: {len(self._active_indices)}")