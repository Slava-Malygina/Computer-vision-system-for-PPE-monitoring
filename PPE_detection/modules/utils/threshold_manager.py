import os
import yaml
from typing import Dict, List
from PyQt5.QtCore import QObject, pyqtSignal

DEFAULT_THRESHOLDS = {
    'head': 0.6,
    'helmet': 0.5,
    'body': 0.6,
    'vest': 0.5,
    'palm': 0.4,
    'glove': 0.3,
    'person': 0.7
}

class ThresholdManager(QObject):
    thresholds_updated = pyqtSignal(str, dict)

    def __init__(self, config_path: str = None):
        super().__init__()
        if config_path is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # project_root = os.path.dirname(current_dir)
            project_root = os.path.dirname(os.path.dirname(current_dir))
            # self.config_path = os.path.join(project_root, 'config', 'config.yaml')
            self.config_path = os.path.join(project_root, 'config', 'config.yaml')
        else:
            self.config_path = config_path
        self._thresholds_by_rtsp: Dict[str, Dict[str, float]] = {}
        self.load_config()


    def load_config(self):
        """Загружает пороги из YAML-файла"""
        if not os.path.exists(self.config_path):
            self._thresholds_by_rtsp = {}
            self.save_config()
            return

        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        self._thresholds_by_rtsp = {
            cam['rtsp_url']: cam.get('detection_thresholds', DEFAULT_THRESHOLDS.copy())
            for cam in data.get('cameras', [])
        }

    def get_thresholds(self, rtsp_url: str) -> Dict[str, float]:
        """Возвращает пороги для камеры по её RTSP-адресу"""
        return self._thresholds_by_rtsp.get(rtsp_url, DEFAULT_THRESHOLDS.copy())

    def set_thresholds(self, rtsp_url: str, new_thresholds: Dict[str, float]):
        """Обновляет пороги для камеры и сохраняет в файл"""
        self._thresholds_by_rtsp[rtsp_url] = new_thresholds
        self.save_config()
        self.thresholds_updated.emit(rtsp_url, new_thresholds)

    def save_config(self):
        """Сохраняет текущие пороги в config.yaml"""
        config_data = {
            'cameras': [
                {
                    'rtsp_url': url,
                    'detection_thresholds': thresholds
                }
                for url, thresholds in self._thresholds_by_rtsp.items()
            ]
        }
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, allow_unicode=True, sort_keys=False)

    def get_all_rtsp_urls(self) -> List[str]:
        """Возвращает список всех RTSP-адресов из конфигурации"""
        return list(self._thresholds_by_rtsp.keys())

    def get_first_4_rtsp_urls(self) -> List[str]:
        """Возвращает первые 4 RTSP-адреса из конфигурации"""
        urls = list(self._thresholds_by_rtsp.keys())
        return urls[:4]

    def threshold_exists(self, rtsp_url: str) -> bool:
        return rtsp_url in self._thresholds_by_rtsp
