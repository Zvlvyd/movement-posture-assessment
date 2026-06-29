# -*- coding: utf-8 -*-
"""
Consolidated YOLO Model Manager — thread-safe lazy-loading singleton.
All services use this single entry point instead of each having its own _get_yolo().
"""
import threading
from typing import Optional, List, Tuple

from config.settings import settings


class ModelManager:
    """
    Thread-safe YOLO model manager.
    Lazily loads one model per model_path, reuses across all callers.

    Usage:
        from models.engine import model_manager
        frame = ...  # BGR numpy array
        kps, confs = model_manager.get_keypoints(frame)
    """

    def __init__(self, model_path: str = None):
        self._model_path = model_path or settings.MODEL_PATH
        self._model = None
        self._lock = threading.Lock()

    def _ensure_loaded(self):
        """Load model if not already loaded (thread-safe, double-checked locking)."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    from ultralytics import YOLO
                    self._model = YOLO(self._model_path)

    @property
    def model(self):
        """Get the underlying YOLO model, loading if needed."""
        self._ensure_loaded()
        return self._model

    def get_keypoints(self, frame):
        """
        Run YOLO-Pose on a BGR frame → (keypoints_xy, confidences) or (None, None).
        Returns the first detected person only.
        keypoints_xy: (17, 2) numpy array
        confidences: list of 17 floats
        """
        self._ensure_loaded()
        results = self._model(frame, verbose=False)
        if results and results[0].keypoints is not None:
            kps = results[0].keypoints.data.cpu().numpy()
            if kps.shape[0] > 0 and kps.shape[1] >= 17:
                kp_xy = kps[0, :, :2]
                kp_conf = kps[0, :, 2].tolist() if kps.shape[1] >= 3 else [1.0] * 17
                return kp_xy, kp_conf
        return None, None

    def get_multi_keypoints(self, frame) -> List[dict]:
        """
        Run YOLO-Pose on a BGR frame → list of person dicts.
        Each dict: {"keypoints": [[x,y], ...], "confidences": [float, ...]}
        Returns empty list if no persons detected.
        """
        self._ensure_loaded()
        results = self._model(frame, verbose=False)
        persons = []
        if results and results[0].keypoints is not None:
            kp_data = results[0].keypoints.data.cpu().numpy()
            for i in range(kp_data.shape[0]):
                kps = kp_data[i]
                persons.append({
                    "keypoints": kps[:, :2].tolist(),
                    "confidences": kps[:, 2].tolist() if kps.shape[1] >= 3 else [1.0] * kps.shape[0],
                })
        return persons

    def get_keypoints_from_b64(self, b64_str: str):
        """
        Decode base64 frame, run YOLO → (keypoints_xy, confidences, frame).
        Returns (None, None, None) on failure.
        """
        from shared.image_utils import decode_base64_frame, resize_frame
        frame = decode_base64_frame(b64_str)
        if frame is None:
            return None, None, None
        frame = resize_frame(frame)
        kp_xy, kp_conf = self.get_keypoints(frame)
        return kp_xy, kp_conf, frame


# Global singleton instance
model_manager = ModelManager()
