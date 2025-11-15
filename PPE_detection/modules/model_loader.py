import os


class ModelLoader:
    def __init__(self):
        self.model = None
        self.model_name = None

    @staticmethod
    def get_model_path():
        base = os.path.dirname(__file__)

        possible_paths = [
            "best_V6.pt",
            "../model/best.pt",
            "resources/best.pt",
            os.path.join(base, "best_V6.pt"),
            os.path.join(base, "model", "best.pt"),
            os.path.join(base, "resources", "best.pt"),
        ]

        for path in possible_paths:
            print(path)
            if os.path.exists(path):
                return path

        return None

    def load(self):
        try:
            from ultralytics import YOLO
            model_path = self.get_model_path()
            print(model_path)
            if model_path and os.path.exists(model_path):
                self.model = YOLO(model_path)
                print(model_path)
                self.model_name = os.path.basename(model_path)
            else:
                demo_path = os.path.join(os.path.dirname(__file__), "../../yolov8n.pt")
                self.model = YOLO(demo_path)
                self.model_name = "yolov8n.pt"
            print(model_path)
            return self.model

        except Exception as e:
            raise RuntimeError(f"Cannot load model: {e}")