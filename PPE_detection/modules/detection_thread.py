from PyQt5.QtCore import pyqtSignal, QThread

class DetectionThread(QThread):
    detection_done = pyqtSignal(object, object, object, object)

    def __init__(self, model, frame, conf_threshold, frame_counter):
        super().__init__()
        self.model = model
        self.frame = frame
        self.conf_threshold = conf_threshold
        self.frame_counter = frame_counter

    def run(self):
        try:
            results = self.model(self.frame,
                                 conf=self.conf_threshold,
                                 verbose=False,
                                 imgsz=640)

            detections = []
            if len(results) > 0 and results[0].boxes is not None:
                for box in results[0].boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = self.model.names[cls]
                    x1, y1, x2, y2 = map(int, box.xyxy[0])

                    detections.append({
                        'cls': class_name,
                        'bbox': [x1, y1, x2, y2],
                        'conf': conf
                    })
            self.detection_done.emit(detections, self.frame, self.frame_counter, results)
        except Exception as e:
            print(f"Detection error: {e}")