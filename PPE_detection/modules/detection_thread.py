from PyQt5.QtCore import pyqtSignal, QThread
import cv2
import numpy as np

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
                    
                    box_area = (x2 - x1) * (y2 - y1)
                    min_area = 50
                    
                    if box_area >= min_area:
                        detections.append({
                            'cls': class_name,
                            'bbox': [x1, y1, x2, y2],
                            'conf': conf,
                            'area': box_area
                        })

            if len(detections) < 3:
                enlarged_frame = self.enhance_small_objects(self.frame)
                enhanced_results = self.model(enlarged_frame,
                                            conf=max(0.15, self.conf_threshold * 0.7),
                                            verbose=False,
                                            imgsz=640)
                
                if len(enhanced_results) > 0 and enhanced_results[0].boxes is not None:
                    for box in enhanced_results[0].boxes:
                        cls = int(box.cls[0])
                        conf = float(box.conf[0])
                        class_name = self.model.names[cls]
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        
                        scale_x = self.frame.shape[1] / enlarged_frame.shape[1]
                        scale_y = self.frame.shape[0] / enlarged_frame.shape[0]
                        
                        x1 = int(x1 * scale_x)
                        y1 = int(y1 * scale_y)
                        x2 = int(x2 * scale_x)
                        y2 = int(y2 * scale_y)
                        
                        box_area = (x2 - x1) * (y2 - y1)
                        
                        is_duplicate = False
                        for existing_det in detections:
                            existing_bbox = existing_det['bbox']
                            iou = self.calculate_iou([x1, y1, x2, y2], existing_bbox)
                            if iou > 0.3:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate and box_area >= 25:
                            detections.append({
                                'cls': class_name,
                                'bbox': [x1, y1, x2, y2],
                                'conf': conf,
                                'area': box_area
                            })

            self.detection_done.emit(detections, self.frame, self.frame_counter, results)
        except Exception as e:
            print(f"Detection error: {e}")

    def enhance_small_objects(self, frame):
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        enhanced = cv2.filter2D(enhanced, -1, kernel)
        
        return enhanced

    def calculate_iou(self, box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter_area = max(0, x2 - x1) * max(0, y2 - y1)
        box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
        box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
        
        union_area = box1_area + box2_area - inter_area
        return inter_area / union_area if union_area > 0 else 0