from PyQt5.QtWidgets import QMessageBox

STYLE_SHEET = """
        QMessageBox {
            background-color: #202020;
            color: #ffffff;
            font-size: 13px;
            border: none;
        }
        QLabel {
            color: #ffffff;
            background-color: transparent;
        }
        QPushButton {
            min-width: 90px;
            padding: 6px 14px;
            background-color: #3a7fff;
            color: #ffffff;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #5a8fff;
        }
    """
ERRORS = {
    "rtsp_lost": {
        "title": "RTSP",
        "icon": QMessageBox.Warning,
        "text": "Потеря соединения с RTSP-потоком",
        "status": "RTSP: потеря соединения"
    },
    "rtsp_open_failed": {
        "title": "RTSP",
        "icon": QMessageBox.Critical,
        "text": "Не удалось подключиться к RTSP-потоку"
    },
    "camera_unavailable": {
        "title": "Камера",
        "icon": QMessageBox.Critical,
        "text": "Камера недоступна",
        "status": "Камера недоступна"
    },
    "camera_lost": {
        "title": "Камера",
        "icon": QMessageBox.Critical,
        "text": "Потеря соединения с камерой"
    },
    "video_open_failed": {
        "title": "Видео",
        "icon": QMessageBox.Critical,
        "text": "Не удалось открыть видеофайл"
    },
    "frame_read_error": {
        "title": "Видео",
        "icon": QMessageBox.Critical,
        "text": "Ошибка чтения видеокадра"
    },
    "internal_error": {
        "title": "Ошибка",
        "icon": QMessageBox.Critical,
        "text": "Внутренняя ошибка приложения"
    }
}

def show_rtsp_error(parent, error_code: str, details: str | None = None) -> str:
    cfg = ERRORS.get(error_code)
    if not cfg:
        return "cancel"

    if cfg.get("status") and hasattr(parent, "status_label"):
        parent.status_label.setText(cfg["status"])

    text = cfg["text"]
    if details:
        text += f"\n\n{details}"

    box = QMessageBox(parent)
    box.setWindowTitle(cfg["title"])
    box.setIcon(cfg["icon"])
    box.setText(text)

    retry_button = box.addButton("Повторить", QMessageBox.AcceptRole)
    cancel_button = box.addButton("Отмена", QMessageBox.RejectRole)

    box.setStyleSheet(STYLE_SHEET)

    box.exec_()

    if box.clickedButton() == retry_button:
        return "retry"
    return "cancel"


def show_error(parent, error_code: str, details: str | None = None) -> None:

    cfg = ERRORS.get(error_code)
    if not cfg:
        QMessageBox.critical(
            parent,
            "Ошибка",
            details or "Неизвестная ошибка"
        )
        return
    status_text = cfg.get("status")
    if status_text and hasattr(parent, "status_label"):
        parent.status_label.setText(status_text)

    text = cfg["text"]
    if details:
        text += f"\n\n{details}"

    box = QMessageBox(parent)
    box.setWindowTitle(cfg["title"])
    box.setIcon(cfg["icon"])
    box.setText(text)

    box.setStyleSheet(STYLE_SHEET)

    box.exec_()