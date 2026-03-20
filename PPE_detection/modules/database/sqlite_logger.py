import sqlite3
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

class SQLiteLogger:

    VALID_VIOLATION_TYPES = {'no_helmet', 'no_vest', 'no_gloves'}

    def __init__(self,
                 db_path: str = '../../db/violations.db',
                 screenshots_dir: str = '../../violations',
                 max_buffer_size: int = 20):

        self.db_path = db_path
        self.screenshots_dir = screenshots_dir
        self.max_buffer_size = max_buffer_size

        self.buffer = []
        self.lock = Lock()

        self.logger = self._setup_logging()

        self._ensure_directories()
        self._connect()
        self._setup_pragmas()
        self._initialize_database()

        self.insert_query = '''
        INSERT INTO violations 
        (date, time, camera_id, human_id, violation_type, confidence, screenshot_path)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        '''

    def _setup_logging(self):
        logger = logging.getLogger(f"SQLiteLogger_{id(self)}")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    def _ensure_directories(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.screenshots_dir).mkdir(parents=True, exist_ok=True)

    def _connect(self):
        self.connection = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def _setup_pragmas(self):
        self.cursor.execute("PRAGMA journal_mode=WAL;")
        self.cursor.execute("PRAGMA synchronous=NORMAL;")
        self.cursor.execute("PRAGMA temp_store=MEMORY;")

    def _initialize_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                human_id INTEGER NOT NULL,
                violation_type TEXT NOT NULL,
                confidence REAL NOT NULL,
                screenshot_path TEXT
            )
        ''')

        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_dt ON violations(date, time)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_cam ON violations(camera_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON violations(violation_type)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_human ON violations(human_id)")

        self.connection.commit()

    def add_violation(self,
                      frame_id: int,
                      human_id: int,
                      violation_type: str,
                      confidence: float,
                      camera_id: str,
                      screenshot_path: str = None):

        if violation_type not in self.VALID_VIOLATION_TYPES:
            return False

        now = datetime.now()

        if screenshot_path is None:
            screenshot_path = f"{self.screenshots_dir}/{camera_id}_{frame_id}_{int(time.time()*1000)}.jpg"

        record = (
            now.strftime('%Y-%m-%d'),
            now.strftime('%H:%M:%S'),
            camera_id,
            int(human_id),
            violation_type,
            float(confidence),
            screenshot_path
        )

        with self.lock:
            self.buffer.append(record)

            if len(self.buffer) >= self.max_buffer_size:
                self._flush_locked()

        return True

    def add_frame_violations(self, frame_id, violations_dict, camera_id, screenshot_path=None):
        count = 0

        for human_key, violations in violations_dict.items():
            try:
                human_id = int(human_key.split('_')[1])
            except:
                continue

            for v in violations:
                if self.add_violation(
                        frame_id,
                        human_id,
                        v.get('violation_type'),
                        v.get('confidence', 0.0),
                        camera_id,
                        screenshot_path
                ):
                    count += 1

        return count


    def flush(self):
        with self.lock:
            return self._flush_locked()

    def _flush_locked(self):
        if not self.buffer:
            return True

        try:
            self.cursor.execute("BEGIN")
            self.cursor.executemany(self.insert_query, self.buffer)
            self.connection.commit()

            self.buffer.clear()
            return True

        except sqlite3.Error as e:
            self.logger.error(f"Flush error: {e}")
            self.connection.rollback()

            try:
                self._connect()
            except:
                pass

            return False

    def get_violations(self,
                       limit=100,
                       offset=0,
                       camera_id=None,
                       violation_type=None,
                       start_date=None,
                       end_date=None,
                       min_confidence=None,
                       sort_by="date",
                       sort_order="DESC",
                       start_time=None,
                       end_time=None,
                       max_confidence=None,
                       ):

        query = "SELECT * FROM violations WHERE 1=1"
        params = []

        if camera_id:
            if isinstance(camera_id, list):
                placeholders = ",".join(["?"] * len(camera_id))
                query += f" AND camera_id IN ({placeholders})"
                params.extend(camera_id)
            else:
                query += " AND camera_id = ?"
                params.append(camera_id)

        if violation_type:
            if isinstance(violation_type, list):
                placeholders = ",".join(["?"] * len(violation_type))
                query += f" AND violation_type IN ({placeholders})"
                params.extend(violation_type)
            else:
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

        if start_time:
            query += " AND time >= ?"
            params.append(start_time)

        if end_time:
            query += " AND time <= ?"
            params.append(end_time)

        if max_confidence is not None:
            query += " AND confidence <= ?"
            params.append(max_confidence)

        allowed_sort_fields = {
            "date": "date",
            "time": "time",
            "confidence": "confidence",
            "camera": "camera_id",
            "type": "violation_type"
        }

        sort_column = allowed_sort_fields.get(sort_by, "date")
        sort_order = "ASC" if sort_order == "ASC" else "DESC"

        query += f" ORDER BY {sort_column} {sort_order}"
        query += " LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        self.cursor.execute(query, params)
        return [dict(row) for row in self.cursor.fetchall()]

    def get_violations_count(self,
                             camera_id=None,
                             violation_type=None,
                             start_date=None,
                             end_date=None,
                             min_confidence=None,
                             start_time=None,
                             end_time=None,
                             max_confidence=None,
                             ):

        query = "SELECT COUNT(*) as c FROM violations WHERE 1=1"
        params = []

        if camera_id:
            if isinstance(camera_id, list):
                placeholders = ",".join(["?"] * len(camera_id))
                query += f" AND camera_id IN ({placeholders})"
                params.extend(camera_id)
            else:
                query += " AND camera_id = ?"
                params.append(camera_id)

        if violation_type:
            if isinstance(violation_type, list):
                placeholders = ",".join(["?"] * len(violation_type))
                query += f" AND violation_type IN ({placeholders})"
                params.extend(violation_type)
            else:
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

        if start_time:
            query += " AND time >= ?"
            params.append(start_time)

        if end_time:
            query += " AND time <= ?"
            params.append(end_time)

        if max_confidence is not None:
            query += " AND confidence <= ?"
            params.append(max_confidence)

        self.cursor.execute(query, params)
        return self.cursor.fetchone()['c']

    def get_count(self) -> int:
        self.cursor.execute("SELECT COUNT(*) as c FROM violations")
        return self.cursor.fetchone()['c']


    def delete_old_records(self, days=365):
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        self.cursor.execute("DELETE FROM violations WHERE date < ?", (cutoff,))
        self.connection.commit()

    def close(self):
        self.flush()
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()