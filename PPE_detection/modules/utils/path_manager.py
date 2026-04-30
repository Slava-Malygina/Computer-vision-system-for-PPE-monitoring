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

        self.config_dir = self.base_dir / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.base_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.violations_dir = self.base_dir / "violations"
        self.violations_dir.mkdir(parents=True, exist_ok=True)

        self.models_dir = self.base_dir / "model"
        self.resources_dir = self.base_dir / "resources"

        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.resources_dir.mkdir(parents=True, exist_ok=True)

    def get_icons_dir(self):
        icons_dir = self.resources_dir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        return str(icons_dir)

    def get_config_path(self, filename="config.yaml"):
        return str(self.config_dir / filename)

    def get_violations_dir(self):
        return str(self.violations_dir)

    def get_fonts_dir(self):
        fonts_dir = self.resources_dir / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)
        return str(fonts_dir)

    def get_font_path(self, font_name):

        return os.path.join(self.get_fonts_dir(), font_name)

    def get_violation_path(self, camera_id, frame_id):
        from datetime import datetime

        today = datetime.now().strftime("%Y-%m-%d")
        screenshot_dir = self.violations_dir / today
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S_%f")[:-3]
        filename = f"frame_{frame_id:06d}_{timestamp}.jpg"
        return str(screenshot_dir / filename)


    def get_model_path(self, model_name="best_12.pt"):
        return os.path.join(self.models_dir, model_name)


    def get_icon_path(self, icon_name):
        return str(self.resources_dir / "icons" / icon_name)

    def get_db_path(self, db_name="violations.db"):
        return str(self.logs_dir / db_name)

    def get_styles_dir(self):
        styles_dir = self.resources_dir / "styles"
        styles_dir.mkdir(parents=True, exist_ok=True)
        return str(styles_dir)

    def get_style_path(self, style_name):
        return os.path.join(self.get_styles_dir(), style_name)


path_manager = PathManager()