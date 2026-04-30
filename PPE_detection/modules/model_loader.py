import os

from modules.utils.path_manager import path_manager


class ModelLoader:
    def __init__(self):
        self.model = None
        self.model_name = None

    @staticmethod
    def get_model_path():

        # Последняя версия модели - визуально показывает лучшие результаты,
        # в папке model - есть последние 5 версии, best - одна из них

        path = path_manager.get_model_path("best_12.pt")
        if os.path.exists(path):
            print(path)
            return path

        return None

    def load(self):
        try:
            from ultralytics import YOLO
            model_path = self.get_model_path()
            if model_path and os.path.exists(model_path):
                self.model = YOLO(model_path)
                self.model_name = os.path.basename(model_path)
            # else:
            #     demo_path = os.path.join(os.path.dirname(__file__), "../../yolov8n.pt")
            #     self.model = YOLO(demo_path)
            #     self.model_name = "yolov8n.pt"
            print(model_path)
            return self.model

        except Exception as e:
            raise RuntimeError(f"Cannot load model: {e}")
