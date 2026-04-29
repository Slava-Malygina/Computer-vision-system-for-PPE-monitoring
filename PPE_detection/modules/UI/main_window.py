import os

from ultralytics import YOLO
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QGuiApplication
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QTabWidget

import atexit
import sys
from PyQt5.QtWidgets import QApplication

from modules.UI.violation_log_window import ViolationLogsTab
from modules.config import APP_ICON_PATH
from modules.database.sqlite_logger import SQLiteLogger
from modules.monitoring_window import MonitoringTab
from modules.utils.style_loader import StyleLoader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPE Monitor")
        self.min_aspect_ratio = 16 / 9
        self.max_aspect_ratio = 4 / 3
        self.setMinimumSize(1024, 768)
        self.setWindowIcon(QIcon(APP_ICON_PATH))
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        stylesheet = StyleLoader.load_stylesheet("main_style.qss")
        self.setStyleSheet(stylesheet)

        self.tab_widget = QTabWidget()
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.tabBar().setVisible(False)
        log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
        self.logger = SQLiteLogger('../../logs/violations.db')

        main_log_path = os.path.join(log_dir, "main_log.csv")

        self.violation_logs_tab = ViolationLogsTab(self.logger, self.tab_widget)
        self.monitoring_window = MonitoringTab(self.logger, self.tab_widget)
        atexit.register(self._safe_exit)
        self.tab_widget.addTab(self.monitoring_window, "Мониторинг")
        self.tab_widget.addTab(self.violation_logs_tab, "Журнал нарушений")
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)


    def _safe_exit(self):
        self.monitoring_window.clean_up()
        try:
            self.logger.flush()
        except Exception as e:
            print(f"Error during final merge: {e}")

    def on_tab_changed(self, index):
        if self.tab_widget.widget(index) == self.violation_logs_tab:
            self.violation_logs_tab._load_page()


    def closeEvent(self, event):
        self._safe_exit()
        event.accept()





if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)

    app.setWindowIcon(QIcon(APP_ICON_PATH))
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    window = MainWindow()
    window.showMaximized()
    window.show()
    sys.exit(app.exec_())
