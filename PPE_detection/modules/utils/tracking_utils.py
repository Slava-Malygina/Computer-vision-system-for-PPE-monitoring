import time

import cv2

from modules.violation_detector import _iou


class TrackingManager:
    def __init__(self):
        self.track_history = []
        self.next_track_id = 0

    def update(self, detections, iou_threshold=0.3):
        """
        Обновляет треки на основе новых детекций.
        Возвращает список треков для текущего кадра.
        """
        current_tracks = []
        used_track_ids = set()
        current_time = time.time()

        self.track_history = [track for track in self.track_history
                              if current_time - track[5] < 30.0]

        person_detections = [det for det in detections if det['cls'] in ['person']]

        active_tracks = [track for track in self.track_history
                         if current_time - track[5] < 5.0]
        inactive_tracks = [track for track in self.track_history
                           if current_time - track[5] >= 5.0]

        unmatched_detections = []

        for det in person_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]
            det_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            best_match = None
            best_score = 0

            for track in active_tracks:
                track_box = [track[0], track[1], track[2], track[3]]
                track_id = track[4]

                if track_id in used_track_ids:
                    continue

                iou_val = _iou(track_box, det_box)

                track_center = ((track[0] + track[2]) / 2, (track[1] + track[3]) / 2)
                distance = ((det_center[0] - track_center[0]) ** 2 +
                            (det_center[1] - track_center[1]) ** 2) ** 0.5

                normalized_distance = max(0, 1 - distance / 300)

                if iou_val > 0.1:
                    score = iou_val * 0.7 + normalized_distance * 0.3
                else:
                    score = normalized_distance * 0.5

                if score > best_score and score > 0.3:
                    best_score = score
                    best_match = track

            if best_match:
                track_id = best_match[4]
                alpha = 0.3
                smoothed_x1 = int(alpha * x1 + (1 - alpha) * best_match[0])
                smoothed_y1 = int(alpha * y1 + (1 - alpha) * best_match[1])
                smoothed_x2 = int(alpha * x2 + (1 - alpha) * best_match[2])
                smoothed_y2 = int(alpha * y2 + (1 - alpha) * best_match[3])

                current_tracks.append((smoothed_x1, smoothed_y1, smoothed_x2, smoothed_y2, track_id, current_time))
                used_track_ids.add(track_id)
            else:
                unmatched_detections.append(det)

        remaining_detections = []

        for det in unmatched_detections:
            x1, y1, x2, y2 = det['bbox']
            det_box = [x1, y1, x2, y2]
            det_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            best_match = None
            best_score = 0

            for track in inactive_tracks:
                track_box = [track[0], track[1], track[2], track[3]]
                track_id = track[4]

                if track_id in used_track_ids:
                    continue

                iou_val = _iou(track_box, det_box)

                track_center = ((track[0] + track[2]) / 2, (track[1] + track[3]) / 2)
                distance = ((det_center[0] - track_center[0]) ** 2 +
                            (det_center[1] - track_center[1]) ** 2) ** 0.5

                normalized_distance = max(0, 1 - distance / 400)

                score = iou_val * 0.6 + normalized_distance * 0.4

                if score > best_score and score > 0.4:
                    best_score = score
                    best_match = track

            if best_match:
                track_id = best_match[4]
                current_tracks.append((x1, y1, x2, y2, track_id, current_time))
                used_track_ids.add(track_id)
            else:
                remaining_detections.append(det)

        for det in remaining_detections:
            x1, y1, x2, y2 = det['bbox']

            is_duplicate = False
            det_box = [x1, y1, x2, y2]
            det_center = ((x1 + x2) / 2, (y1 + y2) / 2)

            for existing_track in current_tracks:
                existing_box = [existing_track[0], existing_track[1], existing_track[2], existing_track[3]]
                existing_center = ((existing_track[0] + existing_track[2]) / 2,
                                   (existing_track[1] + existing_track[3]) / 2)

                iou_val = _iou(existing_box, det_box)
                distance = ((det_center[0] - existing_center[0]) ** 2 +
                            (det_center[1] - existing_center[1]) ** 2) ** 0.5

                if iou_val > 0.5 or distance < 50:
                    is_duplicate = True
                    break

            if not is_duplicate:
                self.next_track_id += 1
                track_id = self.next_track_id
                current_tracks.append((x1, y1, x2, y2, track_id, current_time))
                used_track_ids.add(track_id)

        updated_history = []

        for track in current_tracks:
            updated_history.append(track)

        for track in active_tracks:
            if track[4] not in used_track_ids and current_time - track[5] < 5.0:
                updated_history.append(track)

        inactive_to_keep = [track for track in inactive_tracks
                            if track[4] not in used_track_ids and current_time - track[5] < 15.0]
        updated_history.extend(inactive_to_keep[:5])

        self.track_history = updated_history

        return [(x1, y1, x2, y2, track_id) for x1, y1, x2, y2, track_id, _ in current_tracks]

    def clear(self):
        """Очистка истории трекинга"""
        self.track_history.clear()
        self.next_track_id = 0


def draw_detections_on_frame_with_tracking(frame, detections, tracks, violations_dict):
    display_frame = frame.copy()

    colors = {
        'helmet': (0, 255, 0),
        'vest': (255, 0, 0),
        'gloves': (0, 255, 255),
        'human': (255, 0, 255),
        'person': (255, 0, 255),
        'head': (255, 255, 0),
        'body': (0, 165, 255),
        'palm': (128, 0, 128),
        'wrist': (255, 165, 0),
    }

    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        class_name = det['cls']
        conf = det['conf']

        color = colors.get(class_name, (255, 255, 255))
        label = f"{class_name} {conf:.2f}"

        cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(display_frame, label, (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    for x1, y1, x2, y2, track_id in tracks:
        human_id = f'human_{track_id}'
        track_color = (0, 255, 255)

        if human_id in violations_dict:
            violations_list = violations_dict[human_id]
            if any(v['violation_type'] == 'no_helmet' for v in violations_list):
                track_color = (0, 0, 255)
            elif any(v['violation_type'] == 'no_vest' for v in violations_list):
                track_color = (0, 0, 255)
            elif any(v['violation_type'] == 'no_gloves' for v in violations_list):
                track_color = (0, 0, 255)

        cv2.rectangle(display_frame, (x1, y1), (x2, y2), track_color, 2)

        violation_text = ""
        if human_id in violations_dict:
            violations_list = violations_dict[human_id]
            violation_text = " | ".join([v['violation_type'] for v in violations_list])

        display_text = f"ID:{track_id}"
        if violation_text:
            display_text += f" | {violation_text}"

        cv2.putText(display_frame, display_text, (x1, y1 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, track_color, 2)

    return display_frame


def draw_detections_on_frame(frame, detections):
    colors = {
        'helmet': (0, 255, 0),
        'vest': (255, 0, 0),
        'gloves': (0, 255, 255),
        'human': (255, 0, 255),
        'person': (255, 0, 255),
        'head': (255, 255, 0),
        'body': (0, 165, 255),
        'palm': (128, 0, 128),
        'wrist': (255, 165, 0),
    }
    for det in detections:
        x1, y1, x2, y2 = det['bbox']
        class_name = det['cls']
        conf = det['conf']
        color = colors.get(class_name, (255, 255, 255))
        label = f"{class_name} {conf:.2f}"
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)