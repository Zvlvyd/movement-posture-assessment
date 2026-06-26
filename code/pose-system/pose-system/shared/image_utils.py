# -*- coding: utf-8 -*-
"""
Shared image utilities — base64 decoding, frame resizing, keypoint extraction.
Heavy dependencies (cv2, numpy) are lazy-loaded for modular import compatibility.
"""
import base64
from typing import Optional, Tuple, List


def decode_base64_frame(b64_str: str):
    """
    Decode a base64-encoded JPEG/PNG string into a BGR numpy array (OpenCV frame).
    Returns None if decoding fails.
    """
    if not b64_str:
        return None
    try:
        import numpy as np
        import cv2
        payload = b64_str.split(",")[-1] if "," in b64_str else b64_str
        img_data = base64.b64decode(payload)
        np_arr = np.frombuffer(img_data, np.uint8)
        return cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except Exception:
        return None


def resize_frame(frame, max_width: int = 640):
    """Resize frame to max_width while maintaining aspect ratio."""
    import cv2
    h, w = frame.shape[:2]
    if w > max_width:
        new_h = int(h * max_width / w)
        return cv2.resize(frame, (max_width, new_h))
    return frame


def extract_keypoints_from_frame(frame, yolo_model) -> Tuple[Optional[object], Optional[List[float]]]:
    """
    Run YOLO-Pose on a frame and return keypoints for the first detected person.
    Returns (keypoints_xy, confidences) or (None, None).
    """
    import numpy as np
    results = yolo_model(frame, verbose=False)
    if results and results[0].keypoints is not None:
        kps = results[0].keypoints.data.cpu().numpy()
        if kps.shape[0] > 0 and kps.shape[1] >= 17:
            kp_xy = kps[0, :, :2]
            kp_conf = kps[0, :, 2].tolist() if kps.shape[1] >= 3 else [1.0] * 17
            return kp_xy, kp_conf
    return None, None
