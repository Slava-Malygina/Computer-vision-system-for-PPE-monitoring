def _is_inside(small_box, big_box, threshold=0.5):
    x1, y1, x2, y2 = small_box
    bx1, by1, bx2, by2 = big_box

    inter_x1 = max(x1, bx1)
    inter_y1 = max(y1, by1)
    inter_x2 = min(x2, bx2)
    inter_y2 = min(y2, by2)

    inter_area = max(0, inter_x2 - inter_x1) * max(0, inter_y2 - inter_y1)
    small_area = (x2 - x1) * (y2 - y1)
    if small_area == 0:
        return False

    return (inter_area / small_area) >= threshold


def _iou(boxA, boxB):
    x_a = max(boxA[0], boxB[0])
    y_a = max(boxA[1], boxB[1])
    x_b = min(boxA[2], boxB[2])
    y_b = min(boxA[3], boxB[3])
    inter_area = max(0, x_b - x_a) * max(0, y_b - y_a)
    box_a_area = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    box_b_area = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    return inter_area / float(box_a_area + box_b_area - inter_area + 1e-6)


class ViolationDetector:
    def __init__(self, overlap_thresholds=None, confirmation_frames=3):
        self.overlap_thresholds = overlap_thresholds or {
            'helmet': 0.4,
            'vest': 0.5,
            'glove': 0.3,
            'head': 0.5,
            'body': 0.6,
            'palm': 0.5
        }
        self.confirmation_frames = confirmation_frames
        self.recorded_violations = {}
        self.violation_counters = {}

    def clear_recorded_violations(self):
        self.recorded_violations.clear()
        self.violation_counters.clear()

    def process_frame(self, detections, tracked_objects, frame_id):
        new_violations = {}

        objects_by_class = {}
        for det in detections:
            cls = det['cls']
            objects_by_class.setdefault(cls, []).append(det)

        helmets = objects_by_class.get('helmet', [])
        vests = objects_by_class.get('vest', [])
        gloves = objects_by_class.get('glove', [])
        heads = objects_by_class.get('head', [])
        bodies = objects_by_class.get('body', [])
        palms = objects_by_class.get('palm', [])

        for x1, y1, x2, y2, track_id in tracked_objects:
            person_box = [x1, y1, x2, y2]
            new_person_violations = []

            recorded_for_track = self.recorded_violations.get(track_id, set())

            head_found = [h for h in heads if _is_inside(h['bbox'], person_box, self.overlap_thresholds['head'])]
            helmet_found = [h for h in helmets if _is_inside(h['bbox'], person_box, self.overlap_thresholds['helmet'])]

            head_in_frame = bool(head_found)
            helmet_in_frame = bool(helmet_found)

            head_conf = max((h['conf'] for h in head_found), default=0)
            helmet_conf = max((h['conf'] for h in helmet_found), default=0)

            if track_id not in self.violation_counters:
                self.violation_counters[track_id] = {'no_helmet': 0, 'no_vest': 0, 'no_gloves': 0}
            counters = self.violation_counters[track_id]

            if helmet_in_frame and helmet_conf >= head_conf:
                counters['no_helmet'] = 0
            elif head_in_frame:
                counters['no_helmet'] += 1

            if counters['no_helmet'] >= self.confirmation_frames:
                violation_type = 'no_helmet'
                confidence = round(head_conf, 2)
                if violation_type not in recorded_for_track:
                    new_person_violations.append({'violation_type': violation_type, 'confidence': confidence})
                    if track_id not in self.recorded_violations:
                        self.recorded_violations[track_id] = set()
                    self.recorded_violations[track_id].add(violation_type)

            body_found = [b for b in bodies if _is_inside(b['bbox'], person_box, self.overlap_thresholds['body'])]
            vest_found = [v for v in vests if _is_inside(v['bbox'], person_box, self.overlap_thresholds['vest'])]

            body_in_frame = bool(body_found)
            vest_in_frame = bool(vest_found)

            body_conf = max((b['conf'] for b in body_found), default=0)
            vest_conf = max((v['conf'] for v in vest_found), default=0)

            if track_id not in self.violation_counters:
                self.violation_counters[track_id] = {'no_helmet': 0, 'no_vest': 0, 'no_gloves': 0}
            counters = self.violation_counters[track_id]

            if vest_in_frame and vest_conf >= body_conf:
                counters['no_vest'] = 0
            elif body_in_frame:
                counters['no_vest'] += 1

            if counters['no_vest'] >= self.confirmation_frames:
                violation_type = 'no_vest'
                confidence = round(body_conf, 2)
                if violation_type not in recorded_for_track:
                    new_person_violations.append({'violation_type': violation_type, 'confidence': confidence})
                    if track_id not in self.recorded_violations:
                        self.recorded_violations[track_id] = set()
                    self.recorded_violations[track_id].add(violation_type)

            palm_found = [p for p in palms if _is_inside(p['bbox'], person_box, self.overlap_thresholds['palm'])]
            glove_found = [g for g in gloves if _is_inside(g['bbox'], person_box, self.overlap_thresholds['glove'])]
            palm_in_frame = bool(palm_found)
            glove_in_frame = bool(glove_found)

            palm_conf = max((p['conf'] for p in palm_found), default=0)
            glove_conf = max((g['conf'] for g in glove_found), default=0)

            if track_id not in self.violation_counters:
                self.violation_counters[track_id] = {'no_helmet': 0, 'no_vest': 0, 'no_gloves': 0}
            counters = self.violation_counters[track_id]

            if glove_in_frame and glove_conf >= palm_conf:
                counters['no_gloves'] = 0
            elif palm_in_frame:
                counters['no_gloves'] += 1

            if counters['no_gloves'] >= self.confirmation_frames:
                violation_type = 'no_gloves'
                confidence = round(palm_conf, 2)
                if violation_type not in recorded_for_track:
                    new_person_violations.append({'violation_type': violation_type, 'confidence': confidence})
                    if track_id not in self.recorded_violations:
                        self.recorded_violations[track_id] = set()
                    self.recorded_violations[track_id].add(violation_type)

            if new_person_violations:
                new_violations[f'human_{int(track_id)}'] = new_person_violations

        return {
            'frame_id': frame_id,
            'violations_dict': new_violations,
            'screenshot_path': None
        }
