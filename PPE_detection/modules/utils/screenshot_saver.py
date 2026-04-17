import cv2
import os
from datetime import datetime
from modules.utils.tracking_utils import draw_detections_on_frame_with_tracking
import re


def save_violation_screenshot(frame, detections, tracks, violations_dict, 
                              frame_id, camera_id, output_dir="violations"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]

    safe_camera_id = re.sub(r'[<>:"/\\|?*]', '_', camera_id)
    if camera_id in ["camera", "video"]:
        filename = f"frame_{frame_id:06d}_cam_{safe_camera_id}_{timestamp}.jpg"
    else:
        filename = f"cam_{safe_camera_id}_{timestamp}.jpg"
    filepath = os.path.join(output_dir, filename)
    
    annotated = draw_detections_on_frame_with_tracking(frame.copy(), detections, tracks, violations_dict)
    cv2.imwrite(filepath, annotated)
    if os.path.exists(filepath):
        print(f"[OK] Скриншот сохранён: {filepath}")
    else:
        print(f"[ERROR] Не удалось сохранить: {filepath}")
    return filepath
