import gc
import os
import csv
from datetime import datetime
import logging


class ViolationLogger:
    def __init__(self, output_dir='../../logs', filename=None, max_buffer_size=30):
        self.output_dir = output_dir
        self.max_buffer_size = max_buffer_size
        self.buffer = []
        self._final_merge_done = False
        self.frame_counter = 0
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.logger = self._setup_logging()

        try:
            os.makedirs(output_dir, exist_ok=True)
            self.logger.info(f"Log directory created: {output_dir}")
        except (OSError, PermissionError) as e:
            self.logger.error(f"Error creating log directory {output_dir}: {e}")
            raise

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'violations_log_{timestamp}.csv'

        self.file_path = os.path.join(output_dir, filename)

        try:
            self.fields = ['date', 'frame_id', 'human_id', 'processing_time', 'violation_type',
                           'violation_probability', 'screenshot_path']
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
            self.logger.info(f"Log file initialized: {self.file_path}")

        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Error initializing log file {self.file_path}: {e}")
            raise

    def _setup_logging(self):
        logger = logging.getLogger(f"ViolationLogger_{id(self)}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _get_current_time(self):
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        if current_date != self.current_date:
            self.current_date = current_date
            self.logger.info(f"Смена даты: {self.current_date}")

        return now.strftime('%H:%M:%S.%f')[:-3]

    def add_frame_violations(self, frame_id: int, violations_dict: dict, screenshot_path: str = None):
        try:
            if not violations_dict or not isinstance(violations_dict, dict):
                self.logger.warning(f"Empty or invalid violation data for frame_id={frame_id}")
                return

            for human_id, human_violations in violations_dict.items():
                if not isinstance(human_violations, list):
                    self.logger.warning(f"Expected a list of violations for {human_id}, got: {type(human_violations)}")
                    continue

                for v in human_violations:
                    self.buffer.append({
                        "date": self.current_date,
                        "frame_id": frame_id,
                        "processing_time": self._get_current_time(),
                        "violation_type": v.get('violation_type', 'unknown'),
                        "violation_probability": v.get("probability", 0.0),
                        "screenshot_path": screenshot_path or '',
                        "human_id": human_id
                    })
                    self.logger.info(f"[Frame {frame_id}] {human_id}: {v['violation_type']} "
                                     f"(вероятность {v['probability']})")

            if len(self.buffer) >= self.max_buffer_size:
                self.flush()

        except Exception as e:
            self.logger.error(f"Error adding violations for frame_id {frame_id}: {e}")

    def _flush_buffer(self):
        if not self.buffer:
            return True
        try:
            with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writerows(self.buffer)
            self.logger.debug(f"Записано {len(self.buffer)} записей в файл")
            self.buffer.clear()
            gc.collect()
            return True

        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Ошибка записи буфера в файл: {e}")
            return False

    def flush(self):
        return self._flush_buffer()

    def get_file_path(self):
        return self.file_path

    def read_log(self, limit=None):
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                records = list(reader)

                if limit:
                    records = records[:limit]
            return records

        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Ошибка чтения файла лога: {e}")
            return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        self.logger.info("ViolationLogger exit")
        return False

    def merge_session_logs(self, master_file=None):
        if self._final_merge_done:
            return True

        if master_file is None:
            master_file = os.path.join(os.path.dirname(self.file_path), "main_log.csv")

        abs_master = os.path.abspath(master_file)
        if not os.path.exists(self.file_path):
            self.logger.warning(f"Session log not found: {self.file_path}")
            return False

        try:
            os.makedirs(os.path.dirname(abs_master), exist_ok=True)
            with open(self.file_path, 'r', encoding='utf-8') as sf:
                reader = csv.DictReader(sf)
                rows = list(reader)
                if not rows:
                    self.logger.info(f"No data to merge from {self.file_path}")
                    return False
                fieldnames = reader.fieldnames

            file_exists = os.path.exists(abs_master)

            with open(abs_master, 'a', newline='', encoding='utf-8') as mf:
                writer = csv.DictWriter(mf, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerows(rows)

            self.logger.info(f"Merged {len(rows)} records from {self.file_path} → {abs_master}")
            self._final_merge_done = True
            return True

        except Exception as e:
            self.logger.error(f"Error merging session log: {e}")
            return False

