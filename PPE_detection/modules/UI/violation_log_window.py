import csv
import os
from datetime import datetime, time as dt_time
from PyQt5.QtWidgets import (QVBoxLayout, QHBoxLayout,
                             QWidget, QTableWidget, QHeaderView, QTableWidgetItem, QPushButton, QLabel, QComboBox)
from PyQt5.QtWidgets import QFileDialog
from PPE_detection.modules.UI.filter_panel import FilterPanel
from PPE_detection.modules.UI.pagination_panel import PaginationPanel

from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtCore import Qt, QSize, QDate

from PPE_detection.modules.utils.export_log import export_to_csv, export_to_xlsx, export_to_pdf


class ViolationLogsTab(QWidget):
    def __init__(self, master_log_path="../../logs/main_log.csv"):
        super().__init__()
        self.master_log_path = master_log_path
        self.data_loaded = False
        self.current_filtered_data = []
        self.current_page = 1
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        horizontal_layout = QHBoxLayout(self)
        log_layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setItemDelegate(PaddingDelegate(left=8))

        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Дата", "Время", "ID нарушителя", "Тип нарушения", "Вероятность нарушения", "Путь к скриншоту"
        ])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
                    QTableWidget {
                        background-color: #1a1f25;
                        alternate-background-color: #222831;
                        color: #ffffff;
                        border-radius: 8px; 
                        border: 1px solid #2a2e35;
                    }
                    QHeaderView::section {
                        background-color: #2a2e35;
                        color: #8a94a6;
                        padding: 6px;
                        border: none;
                    }
                        QTableWidget::item {
                        padding-left: 8px;  
                    }
                    QTableWidget::item:selected {
                        background-color: #3a7fff;
                        color: #ffffff;
                    }
                """)
        self.table.verticalHeader().setVisible(False)
        self.filter_panel = FilterPanel()
        self.filter_panel.downloadRequested.connect(self.download_report)
        self.filter_panel.apply_btn.clicked.connect(self.apply_filters)
        self.filter_panel.reset_btn.clicked.connect(self.reset_filters)

        per_page_layout = QHBoxLayout()
        per_page_layout.setAlignment(Qt.AlignRight)


        label = QLabel("Строк на странице:")
        label.setStyleSheet("color: #b0b0b0; font-size: 13px;")

        self.per_page_combo = QComboBox()
        self.per_page_combo.addItems(["10", "25", "50", "100"])
        self.per_page_combo.setCurrentText("25")
        self.per_page_combo.setFixedWidth(80)

        per_page_layout.addWidget(label)
        per_page_layout.addWidget(self.per_page_combo)

        log_layout.addLayout(per_page_layout)
        log_layout.addWidget(self.table)
        horizontal_layout.addLayout(log_layout, stretch=5)
        horizontal_layout.addWidget(self.filter_panel, stretch=2)
        main_layout.addLayout(horizontal_layout)
        self.refresh_btn = QPushButton("Обновить")


        self.refresh_btn.setIconSize(QSize(24, 24))
        self.refresh_btn.setToolTip("Обновить")
        self.refresh_btn.clicked.connect(self.reload_logs)

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
        self.per_page_combo.currentTextChanged.connect(self._on_per_page_changed)
        right_layout = QHBoxLayout()
        right_layout.addStretch()
        pages_reload_layout.addLayout(right_layout, stretch=1)

        log_layout.addLayout(pages_reload_layout)


    def load_logs_once(self):
        if not self.data_loaded:
            self.reload_logs()
            self.data_loaded = True

    def reload_logs(self):
        self.all_logs = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(script_dir, self.master_log_path)


        if not os.path.exists(log_path):
            self.all_logs = []
            self.display_filtered_logs({})
            return

        try:
            with open(log_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.all_logs = rows
        except Exception as e:
            self.all_logs = []

        self.data_loaded = True
        self.display_filtered_logs({})

    def apply_filters(self):
        try:
            params = self.filter_panel.get_filter_params()
            self.display_filtered_logs(params)
        except Exception as e:
            import traceback
            traceback.print_exc()

    def reset_filters(self):
        self.display_filtered_logs({})

    def safe_str(value):
        return str(value) if value is not None else ""
    def display_filtered_logs(self, params):
        try:
            filtered = self.all_logs.copy()

            if params.get("violations"):
                violation_set = set(params["violations"])
                filtered = [
                    row for row in filtered
                    if self.violation_matches(row, violation_set)
                ]

            if "date_from" in params and "date_to" in params:
                date_from = params["date_from"]
                date_to = params["date_to"]
                filtered = [
                    row for row in filtered
                    if date_from <= self.parse_date(row.get("date", "")) <= date_to
                ]

            if "time_from" in params and "time_to" in params:
                time_from = params["time_from"]
                time_to = params["time_to"]
                filtered = [
                    row for row in filtered
                    if time_from <= self.parse_time(row.get("processing_time", "")) <= time_to
                ]

            if "prob_min" in params and "prob_max" in params:
                pmin, pmax = params["prob_min"], params["prob_max"]
                filtered = [
                    row for row in filtered
                    if pmin <= self.parse_probability(row.get("violation_probability", "0")) <= pmax
                ]

            if "sort_field" in params:
                sort_key_map = {
                    "Дата": lambda r: self.parse_date(r.get("date", "")),
                    "Время": lambda r: self.parse_time(r.get("processing_time", "")),
                    "ID нарушителя": lambda r: self.natural_sort_key(r.get("human_id", "")),
                    "Тип нарушения": lambda r: r.get("violation_type", ""),
                    "Вероятность": lambda r: self.parse_probability(r.get("violation_probability", "0")),
                }
                key_func = sort_key_map.get(params["sort_field"], lambda r: r.get("date", ""))
                reverse = (params.get("sort_order", "") == "По убыванию")
                try:
                    filtered.sort(key=key_func, reverse=reverse)
                except Exception as e:
                    print("Ошибка сортировки:", e)

            self.current_filtered_data = filtered
            self.current_page = 1
            self._apply_pagination()
        except:
            import traceback
            traceback.print_exc()

    def _apply_pagination(self):
        self.per_page_combo.blockSignals(True)
        self.pagination.pageChanged.disconnect(self._on_page_changed)

        try:
            per_page = int(self.per_page_combo.currentText())
            total = len(self.current_filtered_data)
            total_pages = max(1, (total + per_page - 1) // per_page)

            self.pagination.set_total_pages(total_pages)
            self.pagination.set_current_page(self.current_page)

            start = (self.current_page - 1) * per_page
            end = start + per_page
            page_data = self.current_filtered_data[start:end]

            self.table.setRowCount(len(page_data))
            for row_idx, row in enumerate(page_data):
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(row.get("date", "") or "")))
                self.table.setItem(row_idx, 1, QTableWidgetItem(str(row.get("processing_time", "") or "")))
                self.table.setItem(row_idx, 2, QTableWidgetItem(str(row.get("human_id", "") or "")))
                violation_type_raw = row.get("violation_type", "") or ""
                violation_display = {
                    "no_helmet": "Без каски",
                    "no_vest": "Без жилета",
                    "no_gloves": "Без перчаток"
                }.get(violation_type_raw, violation_type_raw)
                self.table.setItem(row_idx, 3, QTableWidgetItem(str(violation_display)))
                self.table.setItem(row_idx, 4, QTableWidgetItem(str(row.get("violation_probability", "") or "")))
                self.table.setItem(row_idx, 5, QTableWidgetItem(str(row.get("screenshot_path", "") or "")))
        finally:
            self.pagination.pageChanged.connect(self._on_page_changed)
            self.per_page_combo.blockSignals(False)
    def _on_page_changed(self, page: int):
        self.current_page = page
        self._apply_pagination()

    def _on_per_page_changed(self, text: str):
        self.current_page = 1
        self._apply_pagination()

    def natural_sort_key(self, s):
        import re
        return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

    def parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    def parse_time(self, time_str):
        try:
            if '.' in time_str:
                time_str = time_str.split('.')[0]
            h, m, s = map(int, time_str.split(':'))
            return dt_time(h, m, s)
        except (ValueError, TypeError):
            return dt_time.min

    def parse_probability(self, prob_str):
        try:
            return float(prob_str)
        except:
            return 0.0

    def violation_matches(self, row, allowed_violations):
        violation_map = {
            "no_helmet": "Без каски",
            "no_vest": "Без жилета",
            "no_gloves": "Без перчаток"
        }

        violation_code = row.get("violation_type", "").strip()
        if not violation_code:
            return False

        displayed_name = violation_map.get(violation_code)
        if not displayed_name:
            return False

        return displayed_name in allowed_violations


    def download_report(self):
        try:
            if self.filter_panel.full_report_radio.isChecked():
                data_to_export = self.all_logs
                report_name = "Полный отчёт"
            else:
                data_to_export = self.current_filtered_data
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



class PaddingDelegate(QStyledItemDelegate):
    def __init__(self, left=8, parent=None):
        super().__init__(parent)
        self.left = left

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignVCenter | Qt.AlignLeft
        option.text = " " * (self.left // 2) + option.text

