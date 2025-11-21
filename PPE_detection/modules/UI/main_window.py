from ultralytics import YOLO
from PyQt5.QtWidgets import QMainWindow, QWidget, QHBoxLayout, QTabWidget

from PPE_detection.modules.monitoring_window import MonitoringTab
from violation_log_window import ViolationLogsTab

import sys
from PyQt5.QtWidgets import QApplication


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PPE Monitor")
        self.setGeometry(100, 100, 1400, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet(self.style_sheet())
        self.tab_widget = QTabWidget()
        self.tab_widget.setMovable(True)
        self.tab_widget.setTabsClosable(False)
        self.tab_widget.tabBar().setMinimumWidth(400)

        self.violation_logs_tab = ViolationLogsTab()
        self.monitoring_window = MonitoringTab()

        self.tab_widget.addTab(self.monitoring_window, "Мониторинг")
        self.tab_widget.addTab(self.violation_logs_tab, "Журнал нарушений")
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        main_layout.addWidget(self.tab_widget)

    def style_sheet(self):
        return """
            QMainWindow {
                background-color: #0f1419;
                color: #0f1419;
            }
            QWidget {
                background-color: #0f1419;
                color: #ffffff;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QTabWidget {
                background-color: #0f1419;
                border: none;
            }
            QTabWidget::pane {
                background-color: #0f1419;
                border: 1px solid #2a2e35;
                background-color: #1a1f25;
            }
            QTabBar::tab {
                background-color: #2a2e35;
                color: #8a94a6;
                padding: 8px 16px;
                margin-right: 2px;
                border-radius: 4px;
                font-family: "Segoe UI";
                font-size: 16px;       
                font-weight: bold;  
            }
            QTabBar::tab:selected {
                background-color: #3a7fff;
                color: #ffffff;
                font-weight: bold;
            }
            QGroupBox {
                border: 1px solid #2a2e35;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
                color: #8a94a6;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #3a7fff;   /* синий фон */
                color: #ffffff;
                border: 1px solid #2a68ff;
                border-radius: 4px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a8fff;
            }
            QPushButton:pressed {
                background-color: #2a5fff;
            }
            QPushButton:disabled {
                background-color: #1a1f25;
                color: #5a6370;
            }
            QComboBox {
                background-color: #2a2e35;
                color: #ffffff;
                border: 1px solid #3a424e;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3a424e;
                height: 6px;
                background: #2a2e35;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3a7fff;
                border: 1px solid #3a7fff;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QProgressBar {
                border: 1px solid #3a424e;
                border-radius: 4px;
                background-color: #2a2e35;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #3a7fff;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #1a1f25;
                color: #ffffff;
                border: 1px solid #2a2e35;
                border-radius: 4px;
                font-family: 'Consolas', monospace;
            }
            QLabel {
                color: #ffffff;
            }
        """

    def on_tab_changed(self, index):
        if self.tab_widget.widget(index) == self.violation_logs_tab:
            self.violation_logs_tab.load_logs_once()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())