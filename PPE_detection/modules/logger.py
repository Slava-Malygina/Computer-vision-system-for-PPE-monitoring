import os
import csv
from datetime import datetime
import logging


class ViolationLogger:
    """
    Класс для ведения журнала нарушений в реальном времени.
    Периодически пишет нарушения в csv файл. Для каждой новой сессии создается новый файл.
    Добавляет нарушения с одного кадра в буфер или сразу в файл.
        frame_id: уникальный идентификатор кадра
        violations_list: список нарушений для кадра
         (должен содержать ключи: 'тип_нарушения', 'вероятность_нарушения')
        screenshot_path: путь к скриншоту
    """

    def __init__(self, output_dir='logs', filename=None, max_buffer_size=100):
        self.output_dir = output_dir
        self.max_buffer_size = max_buffer_size
        self.buffer = []
        self.frame_counter = 0
        self.current_date = datetime.now().strftime('%Y-%m-%d')
        self.logger = self._setup_logging()

        try:
            os.makedirs(output_dir, exist_ok=True)
            self.logger.info(f"Создана директория для логов: {output_dir}")
        except (OSError, PermissionError) as e:
            self.logger.error(f"Ошибка создания директории {output_dir}: {e}")
            raise

        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'violations_log_{timestamp}.csv'

        self.file_path = os.path.join(output_dir, filename)

        try:
            self.fields = self.fields = ['дата', 'frame_id', 'human_id', 'время_обработки', 'тип_нарушения',
                                         'вероятность_нарушения', 'путь_к_скриншоту']
            with open(self.file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()
            self.logger.info(f"Файл лога инициализирован: {self.file_path}")

        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Ошибка инициализации файла лога {self.file_path}: {e}")
            raise

    def _setup_logging(self):
        """Настройка логирования для класса."""
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
        """Быстрое получение текущего времени с миллисекундами."""
        now = datetime.now()
        current_date = now.strftime('%Y-%m-%d')
        if current_date != self.current_date:
            self.current_date = current_date
            self.logger.info(f"Смена даты: {self.current_date}")

        return now.strftime('%H:%M:%S.%f')[:-3]

    def add_frame_violations(self, frame_id: int, violations_dict: dict, screenshot_path: str = None):
        """
        Добавляет нарушения для конкретного кадра.

        violations_dict — структура:
        {
            "human_1": [
                {"тип_нарушения": "нет_каски", "вероятность": 0.93},
                {"тип_нарушения": "нет_жилета", "вероятность": 0.82}
            ],
            "human_2": [
                {"тип_нарушения": "нет_перчаток", "вероятность": 0.88}
            ]
        }
        """

        self.logger.debug(
            f"[DEBUG] frame_id={frame_id}, type={type(violations_dict)}, keys={list(violations_dict.keys())
            if isinstance(violations_dict, dict) else 'N/A'}")

        try:
            if not violations_dict or not isinstance(violations_dict, dict):
                self.logger.warning(f"Пустые или некорректные данные нарушений для frame_id={frame_id}")
                return

            for human_id, human_violations in violations_dict.items():
                if not isinstance(human_violations, list):
                    self.logger.warning(f"Ожидался список нарушений для {human_id}, получено: {type(human_violations)}")
                    continue

                for v in human_violations:
                    self.buffer.append({
                        "дата": self.current_date,
                        "frame_id": frame_id,
                        "время_обработки": self._get_current_time(),
                        "тип_нарушения": v.get('тип_нарушения', 'неизвестно'),
                        "вероятность_нарушения": v.get("вероятность", 0.0),
                        "путь_к_скриншоту": screenshot_path or '',
                        "human_id": human_id
                    })
                    self.logger.info(f"[Frame {frame_id}] {human_id}: {v['тип_нарушения']} "
                                     f"(вероятность {v['вероятность']})")
            if len(self.buffer) >= self.max_buffer_size:
                self.flush()

        except Exception as e:
            self.logger.error(f"Ошибка добавления нарушений для frame_id {frame_id}: {e}")

    def _flush_buffer(self):
        """Записывает буфер в файл."""
        if not self.buffer:
            return True
        try:
            with open(self.file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writerows(self.buffer)

            self.logger.debug(f"Записано {len(self.buffer)} записей в файл")
            self.buffer.clear()
            return True

        except (IOError, PermissionError, csv.Error) as e:
            self.logger.error(f"Ошибка записи буфера в файл: {e}")
            return False

    def _validate_entry(self, entry):
        """Быстрая валидация записи."""
        try:
            return (entry['frame_id'] is not None and
                    entry['дата'] and
                    entry['тип_нарушения'] and
                    0.0 <= entry['вероятность_нарушения'] <= 1.0)
        except (KeyError, TypeError):
            return False

    def flush(self):
        """Принудительная запись буфера в файл."""
        return self._flush_buffer()

    def read_log(self, limit=None):
        """Чтение лога с диска."""
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

    def get_log_stats(self):
        """Быстрая статистика по логу."""
        try:
            records = self.read_log(limit=1000)
            buffer_records = len(self.buffer)
            total_entries = len(records) + buffer_records

            if total_entries == 0:
                return {}

            unique_frames = set(record['frame_id'] for record in records)

            stats = {
                'total_entries': total_entries,
                'frames_processed': len(unique_frames),
                'buffer_size': buffer_records,
                'current_date': self.current_date,
                'date_range': {
                    'start': min(r['дата'] for r in records) if records else self.current_date,
                    'end': max(r['дата'] for r in records) if records else self.current_date
                },
                'violation_types': {}
            }

            for record in records[:100]:
                violation_type = record['тип_нарушения']
                stats['violation_types'][violation_type] = stats['violation_types'].get(violation_type, 0) + 1

            return stats

        except Exception as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            return {}

    def get_file_path(self):
        return self.file_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):

        self.flush()
        self.logger.info("ViolationLogger завершил работу")
        return False
