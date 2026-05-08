import os

from PyQt5.QtGui import QIcon, QColor, QPainter, QFontMetrics
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QWidget, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QComboBox,
                             QSizePolicy, QStyle)
from PyQt5.QtWidgets import QFileDialog


from PyQt5.QtCore import QRect
from PyQt5.QtGui import QTextDocument


from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt, QSize, QDate, QTime

from modules.UI.filter_panel import FilterPanel
from modules.UI.gradient_outline_button import GradientOutlineButton
from modules.UI.pagination_panel import PaginationPanel
from modules.database.sqlite_logger import SQLiteLogger
from modules.utils.export_log import export_to_pdf, export_to_csv, export_to_xlsx
from modules.utils.screenshot_viewer import ScreenshotViewer
from modules.utils.style_loader import StyleLoader

VIOLATION_MAP = {
    "Без каски": "no_helmet",
    "Без жилета": "no_vest",
    "Без перчаток": "no_gloves"
}

SORT_FIELD_MAP = {
    "Дата": "date",
    "Время": "time",
    "ID нарушителя": "human_id",
    "Тип нарушения": "violation_type",
    "Вероятность": "confidence"
}

SORT_ORDER_MAP = {
    "По возрастанию": "ASC",
    "По убыванию": "DESC"
}


class ViolationLogsTab(QWidget):

    def __init__(self, logger,  main_window):
        super().__init__()
        self.main_window = main_window
        self.pagination = None
        self.refresh_btn = None
        self.per_page_combo = None
        self.filter_panel = None
        self.logger = logger
        self._session_merged = False

        self.data_loaded = False
        self.current_filtered_data = []
        self.current_page = 1
        self.total_records = 0
        self.current_page = 1

        self._loading = False
        self._initializing = True
        self.init_ui()
        self._initializing = False
        self._load_page()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout = QHBoxLayout(self)
        log_layout = QVBoxLayout(self)
        log_layout.setContentsMargins(20, 20, 20, 20)
        self.table = QTableWidget()
        self.table.setItemDelegate(PaddingDelegate(left=8))

        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Дата", "Время", "ID нарушителя", "Тип нарушения", "Вероятность", "ID камеры", "Путь к скриншоту"
        ])
        self.table.setItemDelegateForColumn(6, MultiLineDelegate(self.table))
        self.table.setItemDelegate(PaddingDelegate(left=8))
        self.table.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(False)
        stylesheet = StyleLoader.load_stylesheet("table_style.qss")
        self.table.setStyleSheet(stylesheet)
        self.table.verticalHeader().setVisible(False)
        self.filter_panel = FilterPanel()
        self.filter_panel.downloadRequested.connect(self.download_report)
        self.filter_panel.apply_btn.clicked.connect(self.apply_filters)
        self.filter_panel.reset_btn.clicked.connect(self.reset_filters)

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)



        per_page_layout = QHBoxLayout()
        per_page_layout.setAlignment(Qt.AlignRight)

        label = QLabel("Строк на странице:")
        combo_box_stylesheet = StyleLoader.load_stylesheet("combo_box_general_style.qss")
        self.setStyleSheet(combo_box_stylesheet)
        self.per_page_combo = QComboBox()
        self.per_page_combo.addItems(["10", "25", "50", "100"])
        self.per_page_combo.setStyleSheet(combo_box_stylesheet)
        self.per_page_combo.setCurrentText("25")
        self.per_page_combo.currentTextChanged.connect(self._on_per_page_changed)
        self.per_page_combo.setFixedWidth(80)

        per_page_layout.addWidget(label)
        per_page_layout.addWidget(self.per_page_combo)

        log_layout.addLayout(per_page_layout)
        log_layout.addWidget(self.table)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setObjectName("rightPanel")
        up_btn_layout = QHBoxLayout()
        switch_tap_btn = GradientOutlineButton(
            "Мониторинг",
            left_icon_path="../../resources/icons/ic_log.png",
            right_icon_path="../../resources/icons/ic_arrow.png"
        )
        switch_tap_btn.clicked_callback = self.on_switch_btn_click
        up_btn_layout.addWidget(switch_tap_btn)
        up_btn_layout.setAlignment(switch_tap_btn, Qt.AlignRight)

        right_layout.addLayout(up_btn_layout)
        spacer = QWidget()
        spacer.setFixedWidth(20)
        spacer.setStyleSheet("background-color: transparent;")
        horizontal_layout.addLayout(log_layout, stretch=5)
        horizontal_layout.addWidget(spacer)
        horizontal_layout.addWidget(right_panel, stretch=2)
        right_layout.addWidget(self.filter_panel)
        main_layout.addLayout(horizontal_layout)
        self.refresh_btn = QPushButton()
        self.refresh_btn.setObjectName("refreshButton")
        self.refresh_btn.setIcon(QIcon("../../resources/icons/ic_refresh.png"))
        self.refresh_btn.setIconSize(QSize(24, 24))
        self.refresh_btn.setToolTip("Обновить")
        self.refresh_btn.clicked.connect(self._load_page)
        self.refresh_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        size = 36
        self.refresh_btn.setFixedSize(size, size)
        self.refresh_btn.setIconSize(QSize(24, 24))

        self.pagination = PaginationPanel()
        pages_reload_layout = QHBoxLayout()
        pages_reload_layout.setContentsMargins(0, 5, 0, 0)

        left_layout = QHBoxLayout()
        left_layout.addWidget(self.refresh_btn)
        left_layout.addStretch()
        pages_reload_layout.addLayout(left_layout, stretch=1)

        center_layout = QHBoxLayout()
        center_layout.addStretch()
        center_layout.addWidget(self.pagination)
        center_layout.addStretch()
        pages_reload_layout.addLayout(center_layout, stretch=2)
        self.pagination.pageChanged.connect(self._on_page_changed)
        right_layout = QHBoxLayout()
        right_layout.addStretch()
        pages_reload_layout.addLayout(right_layout, stretch=1)

        log_layout.addLayout(pages_reload_layout)

    def _on_sort_changed(self, column_index):
        column_map = {
            0: "date",
            1: "time",
            3: "type",
            4: "confidence",
            5: "camera"
        }

        if column_index not in column_map:
            return

        new_sort = column_map[column_index]

        if self.sort_by == new_sort:
            self.sort_order = "ASC" if self.sort_order == "DESC" else "DESC"
        else:
            self.sort_by = new_sort
            self.sort_order = "DESC"

        self._load_page()


    def apply_filters(self):
        if self._loading:
            return
        try:
            self.current_page = 1
            self._load_page()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def reset_filters(self):
        if self._loading:
            return
        self.filter_panel.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.filter_panel.date_to.setDate(QDate.currentDate())

        self.filter_panel.time_from.setTime(QTime(0, 0))
        self.filter_panel.time_to.setTime(QTime(23, 59))

        self.filter_panel.prob_slider.slider_min.setValue(0)
        self.filter_panel.prob_slider.slider_max.setValue(100)

        self.current_page = 1
        self._load_page()

    def safe_str(value):
        return str(value) if value is not None else ""

    def _load_page(self):
        if self._loading:
            return
        self._loading = True
        try:
            all_data = self.logger.get_violations(limit=10)
            per_page = int(self.per_page_combo.currentText())
            offset = (self.current_page - 1) * per_page
            params = self.filter_panel.get_filter_params()

            camera_id = None
            if params["cameras"]:
                if len(params["cameras"]) != self.filter_panel.camera_combo.count():
                    camera_id = params["cameras"]

            violation_type = None
            if params["violations"]:
                if len(params["violations"]) != self.filter_panel.type_combo.count():
                    violation_type = [VIOLATION_MAP[v] for v in params["violations"]]

            start_date = params["date_from"].strftime("%Y-%m-%d")
            end_date = params["date_to"].strftime("%Y-%m-%d")

            start_time = params["time_from"].strftime("%H:%M:%S")
            end_time = params["time_to"].strftime("%H:%M:%S")

            min_conf = params["prob_min"]
            max_conf = params["prob_max"]

            sort_by = SORT_FIELD_MAP.get(params["sort_field"], "date")
            sort_order = SORT_ORDER_MAP.get(params["sort_order"], "DESC")

            data = self.logger.get_violations(
                limit=per_page,
                offset=offset,
                camera_id=camera_id,
                violation_type=violation_type,
                start_date=start_date,
                end_date=end_date,
                start_time=start_time,
                end_time=end_time,
                min_confidence=min_conf,
                max_confidence=max_conf,
                sort_by=sort_by,
                sort_order=sort_order
            )

            self.total_records = self.logger.get_violations_count(
                camera_id=camera_id,
                violation_type=violation_type,
                start_date=start_date,
                end_date=end_date,
                start_time=start_time,
                end_time=end_time,
                min_confidence=min_conf,
                max_confidence=max_conf
            )
            print(self.total_records)
            self._update_table(data)
            self._update_pagination(per_page)
        finally:
            self._loading = False

    def _update_table(self, data):
        self.table.setRowCount(len(data))
        self.table.setWordWrap(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        for row_idx, row in enumerate(data):
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(row.get("date", ""))))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(row.get("time", ""))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(row.get("human_id", ""))))

            violation_display = {
                "no_helmet": "Без каски",
                "no_vest": "Без жилета",
                "no_gloves": "Без перчаток"
            }.get(row.get("violation_type", ""), row.get("violation_type", ""))

            self.table.setItem(row_idx, 3, QTableWidgetItem(violation_display))
            self.table.setItem(row_idx, 4, QTableWidgetItem(str(row.get("confidence", ""))))
            self.table.setItem(row_idx, 5, QTableWidgetItem(str(row.get("camera_id", ""))))
            self.table.setItem(row_idx, 6, QTableWidgetItem(str(row.get("screenshot_path", ""))))

            self.table.resizeRowsToContents()
            self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
    def _update_pagination(self, per_page):
        total_pages = max(1, (self.total_records + per_page - 1) // per_page)
        self.pagination.pageChanged.disconnect()
        self.pagination.set_total_pages(total_pages)
        self.pagination.set_current_page(self.current_page)
        self.pagination.pageChanged.connect(self._on_page_changed)

    def _apply_pagination(self):
        self._load_page()

    def _on_page_changed(self, page: int):
        if self._loading:
            return
        self.current_page = page
        self._apply_pagination()

    def _on_per_page_changed(self, text: str):
        if self._loading or self._initializing:
            return
        self.current_page = 1
        self._apply_pagination()

    def download_report(self):
        try:
            if self.filter_panel.full_report_radio.isChecked():
                data_to_export = self.logger.get_violations(limit=10000)
                report_name = "Полный отчёт"
            else:
                data_to_export = self.logger.get_violations(limit=10000)
                report_name = "Отфильтрованный отчёт"

            max_records = self.filter_panel.record_count.value()
            data_to_export = data_to_export[:max_records]

            if not data_to_export:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(self, "Пустой отчёт", "Нет данных для экспорта.")
                return


            fmt = self.filter_panel.format_combo.currentText()

            default_name = f"{report_name}_{QDate.currentDate().toString('yyyy-MM-dd')}"
            if fmt == "CSV":
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Сохранить отчёт", default_name + ".csv", "CSV Files (*.csv)"
                )
                if file_path:
                    export_to_csv(data_to_export, file_path)
            elif fmt == "XLSX":
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Сохранить отчёт", default_name + ".xlsx", "Excel Files (*.xlsx)"
                )
                if file_path:
                    export_to_xlsx(data_to_export, file_path)
            elif fmt == "PDF":
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Сохранить отчёт", default_name + ".pdf", "PDF Files (*.pdf)"
                )
                if file_path:
                    export_to_pdf(data_to_export, file_path)
        except Exception as e:
            import traceback
            traceback.print_exc()
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Ошибка", f"Не удалось создать отчёт:\n{str(e)}")

    def on_switch_btn_click(self):
        self.main_window.setCurrentIndex(0)

    def open_screenshot(self, screenshot_path):
        viewer = ScreenshotViewer(screenshot_path, self)
        viewer.exec_()

    def on_cell_double_clicked(self, row, column):
        if column == 6:
            item = self.table.item(row, column)
            if item and item.text():
                self.open_screenshot(item.text())

class PaddingDelegate(QStyledItemDelegate):
    def __init__(self, left=8, parent=None):
        super().__init__(parent)
        self.left = left

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignVCenter | Qt.AlignLeft
        option.text = " " * (self.left // 2) + (option.text or "")


class MultiLineDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)
        if not text:
            return

        painter.save()

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, QColor(50, 48, 85))

        rect = QRect(option.rect)
        rect.setLeft(rect.left() + 5)
        rect.setRight(rect.right() - 5)
        rect.setBottom(rect.bottom() + 5)

        html = f'<html><head><style>body {{ color: white; font-weight: bold; font-family: "{painter.font().family()}"; font-size: {painter.font().pointSize()}pt; }}</style></head><body>{text}</body></html>'

        doc = QTextDocument()
        doc.setHtml(html)
        doc.setTextWidth(rect.width())

        painter.translate(rect.topLeft())
        doc.drawContents(painter)

        painter.restore()

    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole)
        if not text:
            return QSize(option.rect.width(), 35)

        rect = QRect(option.rect)
        rect.setLeft(rect.left() + 5)
        rect.setRight(rect.right() - 5)

        html = f'<html><head><style>body {{ color: white; font-weight: bold; }}</style></head><body>{text}</body></html>'

        doc = QTextDocument()
        doc.setHtml(html)
        doc.setTextWidth(rect.width())
        height = doc.size().height() + 15

        return QSize(rect.width(), max(int(height), 35))

    def createEditor(self, parent, option, index):
        return None