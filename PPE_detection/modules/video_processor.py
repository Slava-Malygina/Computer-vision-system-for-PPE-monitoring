import os
from datetime import datetime

import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort

from modules.violation_detector import ViolationDetector


def _iou(boxA, boxB):
    x_a = max(boxA[0], boxB[0])
    y_a = max(boxA[1], boxB[1])
    x_b = min(boxA[2], boxB[2])
    y_b = min(boxA[3], boxB[3])
    inter_area = max(0, x_b - x_a) * max(0, y_b - y_a)
    box_a_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    box_b_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return inter_area / float(box_a_area + box_b_area - inter_area + 1e-6)


def _intersection(a, b):
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    w = max(0, x2 - x1)
    h = max(0, y2 - y1)
    return w * h


def _union_area_of_boxes(boxes):
    if not boxes:
        return 0
    min_x = min(b[0] for b in boxes)
    min_y = min(b[1] for b in boxes)
    max_x = max(b[2] for b in boxes)
    max_y = max(b[3] for b in boxes)
    w = max_x - min_x
    h = max_y - min_y
    if w <= 0 or h <= 0:
        return 0
    mask = np.zeros((h, w), dtype=np.uint8)
    for b in boxes:
        x1, y1, x2, y2 = int(b[0] - min_x), int(b[1] - min_y), int(b[2] - min_x), int(b[3] - min_y)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 1
    return int(mask.sum())


def _coverage(a, b):
    x_a, y_a = max(a[0], b[0]), max(a[1], b[1])
    x_b, y_b = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0, x_b - x_a) * max(0, y_b - y_a)
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / area_b if area_b > 0 else 0


def _create_session_folder():
    """Создает уникальную папку для текущей сессии"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_folder = os.path.join("frames", f"session_{timestamp}")
    if not os.path.exists(session_folder):
        os.makedirs(session_folder)
    print(f"Создана папка для скриншотов: {session_folder}")
    return session_folder


def get_adaptive_sizes(frame_shape):
    """Вычисляет адаптивные размеры в зависимости от разрешения видео"""
    height, width = frame_shape[:2]
    total_pixels = height * width

    base_pixels = 1280 * 720

    scale_factor = (total_pixels / base_pixels) ** 0.5

    scale_factor = max(0.8, min(scale_factor, 3.0))

    thickness = max(2, int(2 * scale_factor))
    font_scale = max(0.5, 0.5 * scale_factor)
    font_thickness = max(1, int(2 * scale_factor))

    return thickness, font_scale, font_thickness


def filter_overlapping_boxes(detections, existing_tracks, iou_threshold=0.6, cover_threshold=0.4,
                             track_match_threshold=0.3):
    """
    Фильтрует новые боксы людей, чтобы не добавлять "слипшиеся" боксы.

    detections: [(x, y, w, h, conf, cls), ...] — выход YOLO
    existing_tracks: [[x1, y1, x2, y2], ...] — текущие треки людей
    """
    if not detections:
        return []
    if not existing_tracks:
        return detections

    det_xyxy = []
    person_orig_indices = []
    for idx, det in enumerate(detections):
        box, conf, cls = det[:3]
        if cls not in ('person', 'human'):
            continue
        x, y, w, h = box
        xyxy = [x, y, x + w, y + h]
        det_xyxy.append({'xyxy': xyxy, 'conf': conf})
        person_orig_indices.append(idx)

    n = len(det_xyxy)
    if n <= 1:
        return detections

    to_remove = set()

    for i in range(n):
        if i in to_remove:
            continue
        for j in range(i + 1, n):
            if j in to_remove:
                continue

            a = det_xyxy[i]['xyxy']
            b = det_xyxy[j]['xyxy']
            iou_val = _iou(a, b)
            cov_val = _coverage(a, b)
            print(f"\nСравнение боксов {i} и {j}: IoU={iou_val:.3f}, cover={cov_val:.3f}")

            if iou_val > iou_threshold or cov_val > cover_threshold:

                best_a = 0
                best_b = 0

                for t in existing_tracks:
                    iou_a = _iou(a, t)
                    iou_b = _iou(b, t)

                    area_a = (a[2] - a[0]) * (a[3] - a[1])
                    area_b = (b[2] - b[0]) * (b[3] - b[1])
                    area_t = (t[2] - t[0]) * (t[3] - t[1])

                    size_ratio_a = area_a / (area_t + 1e-6)
                    size_ratio_b = area_b / (area_t + 1e-6)

                    # если размер сильно отличается — уменьшаем значимость IoU
                    if size_ratio_a > 1.5 or size_ratio_a < 0.5:
                        iou_a *= 0.5
                    if size_ratio_b > 1.5 or size_ratio_b < 0.5:
                        iou_b *= 0.5

                    best_a = max(best_a, iou_a)
                    best_b = max(best_b, iou_b)

                print(f"  - схожи между собой. Совпадение с треками: A={best_a:.3f}, B={best_b:.3f}")

                if best_a < track_match_threshold and best_b < track_match_threshold:
                    conf_a = det_xyxy[i]['conf']
                    conf_b = det_xyxy[j]['conf']
                    if conf_a >= conf_b:
                        to_remove.add(j)
                        print(f"  Оба новые - оставляем A (conf={conf_a:.2f}) > B (conf={conf_b:.2f})")
                    else:
                        to_remove.add(i)
                        print(f"  Оба новые - оставляем B (conf={conf_b:.2f}) > A (conf={conf_a:.2f})")

                else:
                    if best_a >= best_b:
                        to_remove.add(j)
                        print("  Оставляем A (ближе к треку)")
                    else:
                        to_remove.add(i)
                        print("  Оставляем B (ближе к треку)")

    kept_person_orig_idxs = {person_orig_indices[i] for i in range(n) if i not in to_remove}

    result = []
    for idx, det in enumerate(detections):
        box, conf, cls = det[:3]
        if cls in ('person', 'human'):
            if idx in kept_person_orig_idxs:
                result.append(det)
        else:
            result.append(det)

    print(f"\n[RESULT] осталось {sum(1 for d in result if d[2] in ('person', 'human'))} людей из {n}")
    return result


class VideoProcessor:
    def __init__(self, model_path, logger, save_frames=True, output_video_path=None):
        self.model = YOLO(model_path)
        self.tracker = DeepSort(max_age=30, n_init=3, max_iou_distance=0.3)
        self.detector = ViolationDetector()
        self.logger = logger
        self.save_frames = save_frames
        self.frames_dir = "frames"
        self.output_video_path = output_video_path
        self.active_boxes = []
        self.frames_dir = _create_session_folder()

        self.class_conf_thresholds = {
            'human': 0.55,
            'helmet': 0.4,
            'vest': 0.5,
            'gloves': 0.4,
            'head': 0.5,
            'body': 0.55,
            'palm': 0.4
        }


        self.class_colors = {
            'helmet': (255, 0, 0),
            'vest': (0, 255, 0),
            'gloves': (200, 150, 255),
            'person': (255, 255, 255),
            'head': (0, 0, 255),
            'body': (0, 255, 255),
            'palm': (0, 165, 255),
        }

        if save_frames and not os.path.exists(self.frames_dir):
            os.makedirs(self.frames_dir)

    def process_video(self, video_path, process_every_nth_frame=15):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"Не удалось открыть видео: {video_path}")
            return
        frame_id = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 5.0
        print(f"Обработка видео {video_path} ({total_frames} кадров")
        video_writer = None
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_id += 1
            if frame_id % process_every_nth_frame != 0:
                continue

            results = self.model.predict(frame, conf=0.1, verbose=False)[0]

            detections = []
            for box, cls, conf in zip(results.boxes.xyxy, results.boxes.cls, results.boxes.conf):
                x1, y1, x2, y2 = map(int, box)
                name = self.model.names[int(cls)]
                threshold = self.class_conf_thresholds.get(name, 0.5)
                if conf < threshold:
                    continue
                detections.append({'cls': name, 'bbox': [x1, y1, x2, y2], 'conf': float(conf)})

            people_boxes = []
            for det in detections:
                if det['cls'] == 'human':
                    x1, y1, x2, y2 = det['bbox']
                    w, h = x2 - x1, y2 - y1
                    people_boxes.append(([x1, y1, w, h], det['conf'], det['cls']))

            people_boxes = filter_overlapping_boxes(people_boxes, self.active_boxes)
            tracks = self.tracker.update_tracks(people_boxes, frame=frame)

            self.active_boxes = [
                tuple(map(int, track.to_ltrb())) for track in tracks if track.is_confirmed()
            ]

            tracked_objects = [(int(t.to_ltrb()[0]), int(t.to_ltrb()[1]),
                                int(t.to_ltrb()[2]), int(t.to_ltrb()[3]), t.track_id)
                               for t in tracks if t.is_confirmed()]

            print("Подтверждённые объекты людей:", tracked_objects)

            track_yolo_matches = {}
            yolo_matched_track_ids = set()

            for t in tracks:
                if t.is_confirmed():
                    track_bbox = tuple(map(int, t.to_ltrb()))

                    best_match = None
                    best_iou = 0

                    for det in detections:
                        if det['cls'] == 'human':
                            det_bbox = tuple(det['bbox'])
                            iou_val = _iou(track_bbox, det_bbox)

                            if iou_val > best_iou and iou_val > 0.3:
                                best_iou = iou_val
                                best_match = det
                    if best_match:
                        track_yolo_matches[t.track_id] = best_match['conf']
                        yolo_matched_track_ids.add(t.track_id)
                    else:
                        track_yolo_matches[t.track_id] = 0.9

            thickness, font_scale, font_thickness = get_adaptive_sizes(frame.shape)

            for t in tracks:
                if t.is_confirmed():
                    x1, y1, x2, y2 = map(int, t.to_ltrb())
                    track_id = t.track_id
                    confidence = track_yolo_matches.get(track_id, 0.8)

                    color = self.class_colors.get('person', (255, 255, 0))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                    source = "YOLO" if track_id in yolo_matched_track_ids else "tracker"
                    label = f'person ID:{track_id} conf:{confidence:.2f} ({source})'

                    cv2.putText(frame, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)

            for det in detections:
                if det['cls'] != 'person' and det['cls'] != 'human':
                    x1, y1, x2, y2 = det['bbox']
                    cls = det['cls']
                    confidence = det['conf']
                    color = self.class_colors.get(cls, (255, 255, 255))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)

                    label = f'{cls} conf:{confidence:.2f}'
                    cv2.putText(frame, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, font_thickness)
            result = self.detector.process_frame(detections, tracked_objects, frame_id)

            if result['violations_dict']:
                print("лог")
                if self.save_frames:
                    screenshot_path = os.path.join(self.frames_dir, f"frame_{frame_id:06d}.jpg")

                    cv2.imwrite(screenshot_path, frame)
                    result['screenshot_path'] = screenshot_path

                self.logger.add_frame_violations(
                    frame_id=result['frame_id'],
                    violations_dict=result['violations_dict'],
                    screenshot_path=result['screenshot_path'],

                )

            if video_writer is None and self.output_video_path:
                h, w = frame.shape[:2]
                video_writer = cv2.VideoWriter(self.output_video_path, fourcc, fps, (w, h))

            if video_writer:
                video_writer.write(frame)

            if frame_id % 10 == 0:
                print(f"Кадр {frame_id}/{total_frames} обработан")

        cap.release()
        if video_writer:
            video_writer.release()
        print("Обработка завершена!")
