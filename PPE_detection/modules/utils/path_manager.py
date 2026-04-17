import sys
import os
from pathlib import Path

class PathManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_paths()
        return cls._instance

    def _init_paths(self):
        """Инициализирует базовые пути приложения"""
        if getattr(sys, 'frozen', False):
            self.base_dir = Path(sys.executable).parent
        else:

            current_file = Path(__file__).resolve()
            self.base_dir = current_file.parent.parent.parent

        self.violations_dir = self.base_dir / "violations"
        self.violations_dir.mkdir(parents=True, exist_ok=True)

    def get_violations_dir(self):

        return str(self.violations_dir)

path_manager = PathManager()