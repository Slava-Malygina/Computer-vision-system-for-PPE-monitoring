import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import QCoreApplication

from modules.video_thread import VideoThread


@pytest.fixture(scope="session")
def qapp():
    app = QCoreApplication([])
    yield app


# ---------- 1. Инициализация с RTSP ----------
def test_rtsp_initialization():
    rtsp_url = "rtsp://127.0.0.1/test"
    vt = VideoThread(source_type="rtsp", source_path=rtsp_url)

    assert vt.source_type == "rtsp"
    assert vt.source_path == rtsp_url
    assert vt.cap is None
    assert vt.is_running is False


@patch("cv2.VideoCapture")
def test_rtsp_unavailable(mock_capture):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_capture.return_value = mock_cap

    vt = VideoThread("rtsp", "rtsp://invalid-url")
    errors = []

    vt.error_occurred.connect(lambda msg: errors.append(msg))
    vt.run()

    assert len(errors) == 1
    assert "RTSP" in errors[0] or "rtsp" in errors[0].lower()


@patch("cv2.VideoCapture")
def test_stop_releases_resources(mock_capture):
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.read.return_value = (False, None)
    mock_capture.return_value = mock_cap

    vt = VideoThread("rtsp", "rtsp://127.0.0.1/test")
    vt.cap = mock_cap
    vt.is_running = True

    vt.stop()

    mock_cap.release.assert_called_once()
    assert vt.is_running is False
