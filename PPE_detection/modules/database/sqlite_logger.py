import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Union
import gc
import json


class SQLiteLogger:
    """
    - Таблица violations с полями: id, date, time, camera_id, human_id,
      violation_type, confidence, screenshot_path
    - Автоматическое создание БД при первом запуске
    - Обработка ошибок подключения с повторными попытками (до 3 раз)
    - Буферизация записей для оптимизации производительности
    - Поддержка фильтрации и экспорта данных
    - Автоматическое удаление скриншотов через 30 дней
    """
    VALID_VIOLATION_TYPES = {'no_helmet', 'no_vest', 'no_gloves'}

    def __init__(self, db_path: str = '../../db/violations.db',
                 screenshots_dir: str = '../../violations',
                 max_buffer_size: int = 30,
                 max_retries: int = 3):
        """
        Инициализация логгера SQLite.

        Args:
            db_path: путь к файлу базы данных SQLite
            screenshots_dir: директория для хранения скриншотов
            max_buffer_size: максимальный размер буфера перед автоматической записью
            max_retries: количество попыток при ошибке записи
        """
        self.db_path = db_path
        self.screenshots_dir = screenshots_dir
        self.max_buffer_size = max_buffer_size
        self.max_retries = max_retries
        self.buffer = []
        self.connection = None
        self.cursor = None
        self.logger = self._setup_logging()
        self._ensure_directories()
        self._initialize_database()
        self.logger.info(f"SQLiteLogger инициализирован. БД: {self.db_path}")

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger(f"SQLiteLogger_{id(self)}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _ensure_directories(self) -> None:
        """Создание директорий для БД и скриншотов."""
        try:
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)

            screenshots_dir = Path(self.screenshots_dir)
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            self.logger.info(f"Директории созданы/проверены: БД={db_dir}, скриншоты={screenshots_dir}")
        except (OSError, PermissionError) as e:
            self.logger.error(f"Ошибка создания директорий: {e}")
            raise

    def _initialize_database(self) -> None:
        """
        Инициализация базы данных и создание таблиц при первом запуске.
        """
        try:
            self._connect()
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    time TIME NOT NULL,
                    camera_id TEXT NOT NULL,
                    human_id INTEGER NOT NULL,
                    violation_type TEXT NOT NULL CHECK (
                        violation_type IN ('no_helmet', 'no_vest', 'no_gloves')
                    ),
                    confidence REAL NOT NULL CHECK (
                        confidence >= 0.0 AND confidence <= 1.0
                    ),
                    screenshot_path TEXT
                )
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_violations_date_time 
                ON violations(date, time)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_violations_camera 
                ON violations(camera_id)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_violations_type 
                ON violations(violation_type)
            ''')

            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_violations_human 
                ON violations(human_id)
            ''')

            self.connection.commit()
            self.logger.info("База данных инициализирована успешно")

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
        finally:
            self._disconnect()

    def _connect(self) -> None:
        """Установка соединения с БД."""
        try:
            if not self.connection:
                self.connection = sqlite3.connect(self.db_path)
                self.connection.row_factory = sqlite3.Row
                self.cursor = self.connection.cursor()
                self.logger.debug("Соединение с БД установлено")
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка подключения к БД: {e}")
            raise

    def _disconnect(self) -> None:
        """Закрытие соединения с БД."""
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            if self.connection:
                self.connection.close()
                self.connection = None
                self.logger.debug("Соединение с БД закрыто")
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка при закрытии соединения с БД: {e}")

    def _validate_violation_data(self, data: Dict[str, Any]) -> bool:
        """
        Валидация данных нарушения перед записью.

        Args:
            data: словарь с данными нарушения

        Returns:
            True если данные корректны, иначе False
        """
        try:
            if data['violation_type'] not in self.VALID_VIOLATION_TYPES:
                self.logger.warning(f"Недопустимый тип нарушения: {data['violation_type']}")
                return False
            confidence = float(data['confidence'])
            if confidence < 0.0 or confidence > 1.0:
                self.logger.warning(f"Недопустимое значение confidence: {confidence}")
                return False
            required_fields = ['date', 'time', 'camera_id', 'human_id',
                               'violation_type', 'confidence']
            for field in required_fields:
                if field not in data or data[field] is None:
                    self.logger.warning(f"Отсутствует обязательное поле: {field}")
                    return False
            if int(data['human_id']) < 1:
                self.logger.warning(f"Недопустимое значение human_id: {data['human_id']}")
                return False

            return True

        except (ValueError, TypeError) as e:
            self.logger.warning(f"Ошибка валидации данных: {e}")
            return False

    def add_violation(self, frame_id: int, human_id: int, violation_type: str,
                      confidence: float, camera_id: str, screenshot_path: str = None) -> bool:
        """
        Добавление одного нарушения в буфер.

        Args:
            frame_id: идентификатор кадра (используется для формирования screenshot_path)
            human_id: ID трека человека
            violation_type: тип нарушения ('no_helmet', 'no_vest', 'no_gloves')
            confidence: уверенность модели (0.0-1.0)
            camera_id: идентификатор камеры
            screenshot_path: путь к скриншоту (если None, будет сгенерирован)

        Returns:
            True если добавлено успешно, иначе False
        """
        now = datetime.now()

        if screenshot_path is None:
            screenshot_path = f"{self.screenshots_dir}/frame_{frame_id:06d}.jpg"
        violation_data = {
            'date': now.strftime('%Y-%m-%d'),
            'time': now.strftime('%H:%M:%S'),
            'camera_id': camera_id,
            'human_id': human_id,
            'violation_type': violation_type,
            'confidence': round(float(confidence), 2),
            'screenshot_path': screenshot_path
        }
        if not self._validate_violation_data(violation_data):
            return False
        self.buffer.append(violation_data)

        self.logger.info(f"[Frame {frame_id}] human_{human_id}: {violation_type} "
                         f"(вероятность {confidence}) camera: {camera_id}")
        if len(self.buffer) >= self.max_buffer_size:
            self.flush()
        return True

    def add_frame_violations(self, frame_id: int, violations_dict: dict,
                             camera_id: str, screenshot_path: str = None) -> int:
        """
        Добавление нарушений за кадр из формата ViolationDetector.

        Args:
            frame_id: идентификатор кадра
            violations_dict: словарь с нарушениями в формате
                           {'human_123': [{'violation_type': 'no_helmet', 'confidence': 0.95}, ...]}
            camera_id: идентификатор камеры
            screenshot_path: путь к скриншоту (если None, будет сгенерирован)
        Returns:
            Количество добавленных нарушений
        """
        if not violations_dict or not isinstance(violations_dict, dict):
            self.logger.warning(f"Пустые или некорректные данные нарушений для frame_id={frame_id}")
            return 0

        count = 0
        for human_key, human_violations in violations_dict.items():
            try:
                human_id = int(human_key.split('_')[1])
            except (IndexError, ValueError):
                self.logger.warning(f"Некорректный формат human_id: {human_key}")
                continue

            if not isinstance(human_violations, list):
                self.logger.warning(f"Ожидался список нарушений для {human_key}, получен: {type(human_violations)}")
                continue

            for v in human_violations:
                if self.add_violation(
                        frame_id=frame_id,
                        human_id=human_id,
                        violation_type=v.get('violation_type', 'unknown'),
                        confidence=v.get('confidence', 0.0),
                        camera_id=camera_id,
                        screenshot_path=screenshot_path
                ):
                    count += 1

        return count

    def flush(self) -> bool:
        """
        Принудительная запись буфера в базу данных.
        При ошибке повторяет попытку до max_retries раз.

        Returns:
            True если запись успешна, False в случае ошибки
        """
        if not self.buffer:
            return True

        for attempt in range(self.max_retries):
            try:
                return self._flush_buffer()
            except Exception as e:
                self.logger.error(f"Попытка {attempt + 1}/{self.max_retries} не удалась: {e}")
                if attempt < self.max_retries - 1:
                    continue
                else:
                    self.logger.error(f"Не удалось записать буфер после {self.max_retries} попыток")
                    return False

    def _flush_buffer(self) -> bool:
        """Внутренний метод записи буфера в БД."""
        try:
            self._connect()
            self.cursor.executemany('''
                INSERT INTO violations 
                (date, time, camera_id, human_id, violation_type, confidence, screenshot_path)
                VALUES 
                (:date, :time, :camera_id, :human_id, :violation_type, :confidence, :screenshot_path)
            ''', self.buffer)

            self.connection.commit()
            self.logger.debug(f"Записано {len(self.buffer)} записей в БД")

            self.buffer.clear()
            gc.collect()

            return True

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка записи буфера в БД: {e}")
            if self.connection:
                self.connection.rollback()
            raise
        finally:
            self._disconnect()

    def get_violations(self,
                       limit: int = 1000,
                       offset: int = 0,
                       camera_id: Optional[str] = None,
                       violation_type: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       min_confidence: Optional[float] = None,
                       human_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Получение записей о нарушениях с фильтрацией.

        Args:
            limit: максимальное количество записей
            offset: смещение для пагинации
            camera_id: фильтр по камере
            violation_type: фильтр по типу нарушения
            start_date: начальная дата (включительно, формат YYYY-MM-DD)
            end_date: конечная дата (включительно, формат YYYY-MM-DD)
            min_confidence: минимальная уверенность
            human_id: фильтр по ID человека

        Returns:
            Список словарей с записями о нарушениях
        """
        try:
            self._connect()

            query = "SELECT * FROM violations WHERE 1=1"
            params = []
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            if violation_type:
                if violation_type in self.VALID_VIOLATION_TYPES:
                    query += " AND violation_type = ?"
                    params.append(violation_type)

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            if min_confidence is not None:
                query += " AND confidence >= ?"
                params.append(min_confidence)

            if human_id is not None:
                query += " AND human_id = ?"
                params.append(human_id)

            query += " ORDER BY date DESC, time DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            self.cursor.execute(query, params)
            rows = self.cursor.fetchall()
            result = [dict(row) for row in rows]

            self.logger.debug(f"Получено {len(result)} записей из БД")
            return result

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения записей из БД: {e}")
            return []
        finally:
            self._disconnect()

    def get_violations_count(self,
                             camera_id: Optional[str] = None,
                             violation_type: Optional[str] = None,
                             start_date: Optional[str] = None,
                             end_date: Optional[str] = None,
                             min_confidence: Optional[float] = None) -> int:
        """
        Получение количества записей с фильтрацией.

        Returns:
            Количество записей, удовлетворяющих фильтрам
        """
        try:
            self._connect()

            query = "SELECT COUNT(*) as count FROM violations WHERE 1=1"
            params = []

            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)

            if violation_type:
                if violation_type in self.VALID_VIOLATION_TYPES:
                    query += " AND violation_type = ?"
                    params.append(violation_type)

            if start_date:
                query += " AND date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND date <= ?"
                params.append(end_date)

            if min_confidence is not None:
                query += " AND confidence >= ?"
                params.append(min_confidence)

            self.cursor.execute(query, params)
            result = self.cursor.fetchone()['count']

            return result

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения количества записей: {e}")
            return 0
        finally:
            self._disconnect()

    def get_statistics(self,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None,
                       camera_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Получение статистики по нарушениям.

        Args:
            start_date: начальная дата (включительно)
            end_date: конечная дата (включительно)
            camera_id: фильтр по камере

        Returns:
            Словарь со статистикой
        """
        try:
            self._connect()
            subquery = "SELECT * FROM violations WHERE 1=1"
            params = []

            if start_date:
                subquery += " AND date >= ?"
                params.append(start_date)

            if end_date:
                subquery += " AND date <= ?"
                params.append(end_date)

            if camera_id:
                subquery += " AND camera_id = ?"
                params.append(camera_id)

            self.cursor.execute(f"SELECT COUNT(*) as count FROM ({subquery})", params)
            total_count = self.cursor.fetchone()['count']

            type_query = f"""
                SELECT violation_type, COUNT(*) as count 
                FROM ({subquery}) 
                GROUP BY violation_type
            """
            self.cursor.execute(type_query, params)
            by_type = {row['violation_type']: row['count'] for row in self.cursor.fetchall()}

            for v_type in self.VALID_VIOLATION_TYPES:
                if v_type not in by_type:
                    by_type[v_type] = 0

            confidence_query = f"""
                SELECT violation_type, AVG(confidence) as avg_confidence
                FROM ({subquery})
                GROUP BY violation_type
            """
            self.cursor.execute(confidence_query, params)
            avg_confidence = {row['violation_type']: round(row['avg_confidence'], 2)
                              for row in self.cursor.fetchall()}

            self.cursor.execute(f"SELECT COUNT(DISTINCT human_id) as count FROM ({subquery})", params)
            unique_people = self.cursor.fetchone()['count']

            daily_query = f"""
                SELECT date, COUNT(*) as count
                FROM ({subquery})
                GROUP BY date
                ORDER BY date
                LIMIT 30
            """
            self.cursor.execute(daily_query, params)
            daily_trend = [{'date': row['date'], 'count': row['count']}
                           for row in self.cursor.fetchall()]

            return {
                'total_violations': total_count,
                'by_type': by_type,
                'avg_confidence': avg_confidence,
                'unique_people': unique_people,
                'daily_trend': daily_trend,
                'period': {
                    'start': start_date or 'all_time',
                    'end': end_date or 'all_time'
                },
                'camera_id': camera_id or 'all_cameras'
            }

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка получения статистики: {e}")
            return {}
        finally:
            self._disconnect()

    def export_to_json(self,
                       file_path: str,
                       camera_id: Optional[str] = None,
                       violation_type: Optional[str] = None,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> bool:
        """
        Экспорт записей в JSON файл.

        Args:
            file_path: путь для сохранения JSON
            camera_id: фильтр по камере
            violation_type: фильтр по типу нарушения
            start_date: начальная дата
            end_date: конечная дата

        Returns:
            True если успешно, иначе False
        """
        try:
            records = self.get_violations(
                limit=10000,
                camera_id=camera_id,
                violation_type=violation_type,
                start_date=start_date,
                end_date=end_date
            )

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(records, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Экспортировано {len(records)} записей в {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка экспорта в JSON: {e}")
            return False

    def clean_old_screenshots(self, days: int = 30) -> int:
        """
        Удаление информации о старых скриншотах из БД.
        Физическое удаление файлов должно выполняться отдельным процессом.

        Args:
            days: количество дней хранения скриншотов

        Returns:
            Количество обновленных записей
        """
        try:
            self._connect()
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            self.cursor.execute(
                "UPDATE violations SET screenshot_path = NULL WHERE date < ?",
                (cutoff_date,)
            )

            updated_count = self.cursor.rowcount
            self.connection.commit()

            self.logger.info(f"Очищены пути к скриншотам для {updated_count} записей старше {days} дней")
            return updated_count

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка очистки путей к скриншотам: {e}")
            return 0
        finally:
            self._disconnect()

    def delete_old_records(self, days: int = 365) -> int:
        """
        Удаление записей старше указанного количества дней (NFR4.2).
        Args:
            days: количество дней хранения записей (минимум 365)
        Returns:
            Количество удаленных записей
        """
        if days < 365:
            self.logger.warning(f"Попытка установить срок хранения {days} дней, но минимум 365 дней. Используется 365.")
            days = 365

        try:
            self._connect()
            cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            self.cursor.execute(
                "DELETE FROM violations WHERE date < ?",
                (cutoff_date,)
            )

            deleted_count = self.cursor.rowcount
            self.connection.commit()

            self.logger.info(f"Удалено {deleted_count} записей старше {days} дней")
            return deleted_count

        except sqlite3.Error as e:
            self.logger.error(f"Ошибка удаления старых записей: {e}")
            return 0
        finally:
            self._disconnect()

    def get_db_path(self) -> str:
        """Получение пути к файлу базы данных."""
        return self.db_path

    def get_screenshots_dir(self) -> str:
        """Получение пути к директории со скриншотами."""
        return self.screenshots_dir

    def check_connection(self) -> bool:
        """Проверка подключения к БД."""
        try:
            self._connect()
            self.cursor.execute("SELECT 1")
            self._disconnect()
            return True
        except:
            return False

    def __enter__(self):
        """Поддержка контекстного менеджера."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Выход из контекстного менеджера.
        Записывает буфер перед закрытием.
        """
        self.flush()
        self.logger.info("SQLiteLogger завершил работу")
        return False