import pytest
from unittest.mock import MagicMock, patch

from modules.camera_manager import CameraManager


class FakeThread:
    def __init__(self, source_type, source_path):
        self.source_type = source_type
        self.source_path = source_path
        self.started = False

        self.error_occurred = MagicMock()
        self.frame_ready = MagicMock()
        self.status_update = MagicMock()

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def wait(self, timeout):
        pass

    def deleteLater(self):
        pass


@pytest.fixture
def manager():
    return CameraManager()


@patch("modules.camera_manager.VideoThread", FakeThread)
def test_add_camera(manager):
    index = manager.add_camera("rtsp", "test_stream")

    assert index == 0
    assert manager.camera_count() == 1


@patch("modules.camera_manager.VideoThread", FakeThread)
def test_remove_camera(manager):
    index = manager.add_camera("rtsp", "test_stream")

    manager.remove_camera(index)

    assert manager.camera_count() == 0


@patch("modules.camera_manager.VideoThread", FakeThread)
def test_start_camera(manager):
    index = manager.add_camera("rtsp", "test_stream")

    manager.start_camera(index)

    assert manager.is_active(index)


@patch("modules.camera_manager.VideoThread", FakeThread)
def test_stop_camera(manager):
    index = manager.add_camera("rtsp", "test_stream")

    manager.start_camera(index)
    manager.stop_camera(index)

    assert not manager.is_active(index)


@patch("modules.camera_manager.VideoThread", FakeThread)
def test_start_all(manager):
    manager.add_camera("rtsp", "cam1")
    manager.add_camera("rtsp", "cam2")

    manager.start_all()

    assert manager.is_active(0)
    assert manager.is_active(1)


@patch("modules.camera_manager.VideoThread", FakeThread)
def test_stop_all(manager):
    manager.add_camera("ip-camera", "cam1")
    manager.add_camera("ip-camera", "cam2")

    manager.start_all()
    manager.stop_all()

    assert not manager.is_active(0)
    assert not manager.is_active(1)