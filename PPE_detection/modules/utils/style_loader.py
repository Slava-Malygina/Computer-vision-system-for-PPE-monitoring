import os

from modules.utils.path_manager import path_manager


class StyleLoader:
    @staticmethod
    def load_stylesheet(qss_file_name):
        styles_dir = path_manager.get_styles_dir()

        qss_path = os.path.join(styles_dir, qss_file_name)
        if not os.path.exists(qss_path):
            raise FileNotFoundError(f"Style file not found: {qss_path}")

        with open(qss_path, 'r', encoding='utf-8') as f:
            return f.read()
