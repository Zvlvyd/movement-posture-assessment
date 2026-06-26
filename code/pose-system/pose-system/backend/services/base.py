# -*- coding: utf-8 -*-
"""
Base WebSocket handler — shared functionality for all real-time services.
Provides shared YOLO inference, frame decoding, and angle calculation.
"""
import json
from typing import Optional
from fastapi import WebSocket
from sqlalchemy.orm import Session

from models.angle_calculator import AngleCalculator
from models.engine import model_manager
from shared.image_utils import decode_base64_frame, resize_frame


class BaseWebSocketHandler:
    """
    Base class for WebSocket handlers (Training, Assessment, FMS, Learning, Verification).

    Provides shared:
      - YOLO model access via model_manager (lazy-loaded singleton)
      - Base64 frame decoding + resize
      - Angle computation from keypoints
    """

    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()

    # ── Frame Processing ─────────────────────────────

    def decode_frame(self, b64_str: str):
        """Decode base64 image to BGR frame (or None)."""
        frame = decode_base64_frame(b64_str)
        if frame is not None:
            frame = resize_frame(frame)
        return frame

    def extract_keypoints(self, frame):
        """Run YOLO on a frame → (keypoints_xy, confidences) or (None, None)."""
        return model_manager.get_keypoints(frame)

    def extract_keypoints_from_b64(self, b64_str: str):
        """Decode base64 + YOLO → (keypoints_xy, confidences, frame)."""
        return model_manager.get_keypoints_from_b64(b64_str)

    # ── Angle Computation ────────────────────────────

    def compute_angles(self, keypoints) -> dict:
        """Compute all joint angles from keypoints array."""
        return self.angle_calc.compute_all_angles(keypoints)

    # ── Lifecycle ─────────────────────────────────────

    def cleanup(self):
        """Called on disconnect. Override in subclass if needed."""
        pass
