import os
from datetime import datetime, timedelta
from modules.utils.path_manager import path_manager


class CleanupManager:
    def __init__(self):
        self.path_manager = path_manager

    def cleanup_old_screenshots(self, days=30):
        """Удаляет скриншоты старше указанного количества дней"""
        violations_dir = self.path_manager.get_violations_dir()
        if not os.path.exists(violations_dir):
            return 0

        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days)

        for root, dirs, files in os.walk(violations_dir):
            for file in files:
                if file.endswith('.jpg'):
                    file_path = os.path.join(root, file)
                    try:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime < cutoff_date:
                            os.remove(file_path)
                            deleted_count += 1
                    except Exception as e:
                        print(f"Ошибка удаления {file_path}: {e}")
        return deleted_count


cleanup_manager = CleanupManager()
