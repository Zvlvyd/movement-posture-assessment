# -*- coding: utf-8 -*-
"""
Base WebSocket handler — shared functionality for all real-time services.

Provides:
  - YOLO model access via model_manager (lazy-loaded singleton)
  - Base64 frame decoding + resize
  - Single-person and multi-person keypoint extraction
  - Angle computation from keypoints

Subclasses override process_message() to implement domain-specific logic.
"""
import json
import base64
import cv2
import numpy as np
from typing import Optional, List, Dict
from fastapi import WebSocket
from sqlalchemy.orm import Session

from models.angle_calculator import AngleCalculator
from models.engine import model_manager


class BaseWebSocketHandler:
    """
    Base class for WebSocket handlers (FMS, Assessment, Learning, Verification).

    Usage:
        class MyHandler(BaseWebSocketHandler):
            async def handle_message(self, ws, msg):
                kps, confs, frame = self.extract_keypoints_from_msg(msg)
                if kps is not None:
                    angles = self.compute_angles(kps)
                    # ... domain logic
    """

    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()

    # ── Frame Processing ─────────────────────────────────

    def decode_frame(self, b64_str: str) -> Optional[np.ndarray]:
        """Decode base64 image to BGR frame (resized to 640px), or None."""
        try:
            img_data = base64.b64decode(b64_str.split(",")[-1] if "," in b64_str else b64_str)
            np_arr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None:
                return None
            h, w = frame.shape[:2]
            if w > 640:
                frame = cv2.resize(frame, (640, int(h * 640 / w)))
            return frame
        except Exception:
            return None

    def extract_keypoints(self, frame) -> tuple:
        """Run YOLO on a frame → (keypoints_xy, confidences) or (None, None)."""
        return model_manager.get_keypoints(frame)

    def extract_keypoints_from_b64(self, b64_str: str) -> tuple:
        """Decode base64 + YOLO → (keypoints_xy, confidences, frame)."""
        frame = self.decode_frame(b64_str)
        if frame is None:
            return None, None, None
        kp_xy, kp_conf = model_manager.get_keypoints(frame)
        return kp_xy, kp_conf, frame

    def extract_multi_keypoints(self, frame) -> List[dict]:
        """Run YOLO on a frame → list of person dicts (multi-person)."""
        return model_manager.get_multi_keypoints(frame)

    def extract_keypoints_from_msg(self, msg: dict, key: str = "data") -> tuple:
        """Extract keypoints from a WebSocket message dict.

        Args:
            msg: The parsed JSON message.
            key: The key containing the base64 image ("data" or "image").

        Returns:
            (keypoints_xy, confidences, frame) or (None, None, None).
        """
        b64 = msg.get(key, "")
        if not b64:
            return None, None, None
        return self.extract_keypoints_from_b64(b64)

    # ── Angle Computation ────────────────────────────────

    def compute_angles(self, keypoints) -> dict:
        """Compute all joint angles from keypoints array."""
        return self.angle_calc.compute_all_angles(keypoints)

    # ── WebSocket Helpers ────────────────────────────────

    async def send_json(self, ws: WebSocket, data: dict):
        """Send JSON data over WebSocket, ignoring errors."""
        try:
            await ws.send_json(data)
        except Exception:
            pass

    async def send_error(self, ws: WebSocket, message: str):
        """Send an error message over WebSocket."""
        await self.send_json(ws, {"type": "error", "message": message})

    # ── Lifecycle ─────────────────────────────────────────

    def cleanup(self):
        """Called on disconnect. Override in subclass if needed."""
        pass
