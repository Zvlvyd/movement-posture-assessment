import numpy as np
from typing import Dict, List, Tuple, Optional

# COCO 17 keypoint indices
KP = {
    'nose': 0, 'left_eye': 1, 'right_eye': 2, 'left_ear': 3, 'right_ear': 4,
    'left_shoulder': 5, 'right_shoulder': 6, 'left_elbow': 7, 'right_elbow': 8,
    'left_wrist': 9, 'right_wrist': 10, 'left_hip': 11, 'right_hip': 12,
    'left_knee': 13, 'right_knee': 14, 'left_ankle': 15, 'right_ankle': 16
}

def calc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    ba = a - b
    bc = c - b
    cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))

def calc_vertical_angle(a: np.ndarray, b: np.ndarray) -> float:
    ab = b - a
    vertical = np.array([0.0, -1.0])
    cos_angle = np.dot(ab, vertical) / (np.linalg.norm(ab) + 1e-8)
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))

class AngleCalculator:
    def __init__(self):
        self.kp = KP
    
    def get_kp(self, keypoints: np.ndarray, idx: int) -> Optional[np.ndarray]:
        if idx >= len(keypoints):
            return None
        # keypoints may be (17,2) [x,y] or (17,3) [x,y,conf]
        if keypoints.shape[1] >= 3 and keypoints[idx][2] < 0.3:
            return None
        return keypoints[idx][:2]
    
    def compute_all_angles(self, keypoints: np.ndarray) -> Dict[str, Optional[float]]:
        angles = {}
        
        left_hip = self.get_kp(keypoints, KP['left_hip'])
        right_hip = self.get_kp(keypoints, KP['right_hip'])
        left_knee = self.get_kp(keypoints, KP['left_knee'])
        right_knee = self.get_kp(keypoints, KP['right_knee'])
        left_ankle = self.get_kp(keypoints, KP['left_ankle'])
        right_ankle = self.get_kp(keypoints, KP['right_ankle'])
        left_shoulder = self.get_kp(keypoints, KP['left_shoulder'])
        right_shoulder = self.get_kp(keypoints, KP['right_shoulder'])
        left_elbow = self.get_kp(keypoints, KP['left_elbow'])
        right_elbow = self.get_kp(keypoints, KP['right_elbow'])
        left_wrist = self.get_kp(keypoints, KP['left_wrist'])
        right_wrist = self.get_kp(keypoints, KP['right_wrist'])
        nose = self.get_kp(keypoints, KP['nose'])
        
        if left_hip is not None and left_knee is not None and left_ankle is not None:
            angles['left_knee'] = calc_angle(left_hip, left_knee, left_ankle)
        if right_hip is not None and right_knee is not None and right_ankle is not None:
            angles['right_knee'] = calc_angle(right_hip, right_knee, right_ankle)
        if left_shoulder is not None and left_hip is not None and left_knee is not None:
            angles['left_hip'] = calc_angle(left_shoulder, left_hip, left_knee)
        if right_shoulder is not None and right_hip is not None and right_knee is not None:
            angles['right_hip'] = calc_angle(right_shoulder, right_hip, right_knee)
        if left_elbow is not None and left_shoulder is not None and left_hip is not None:
            angles['left_shoulder'] = calc_angle(left_elbow, left_shoulder, left_hip)
        if right_elbow is not None and right_shoulder is not None and right_hip is not None:
            angles['right_shoulder'] = calc_angle(right_elbow, right_shoulder, right_hip)
        if left_shoulder is not None and left_elbow is not None and left_wrist is not None:
            angles['left_elbow'] = calc_angle(left_shoulder, left_elbow, left_wrist)
        if right_shoulder is not None and right_elbow is not None and right_wrist is not None:
            angles['right_elbow'] = calc_angle(right_shoulder, right_elbow, right_wrist)
        
        if left_shoulder is not None and right_shoulder is not None and left_hip is not None and right_hip is not None:
            mid_shoulder = (left_shoulder + right_shoulder) / 2.0
            mid_hip = (left_hip + right_hip) / 2.0
            angles['trunk_tilt'] = calc_vertical_angle(mid_hip, mid_shoulder)
        
        if nose is not None and left_shoulder is not None and right_shoulder is not None:
            mid_shoulder = (left_shoulder + right_shoulder) / 2.0
            angles['neck_tilt'] = calc_vertical_angle(mid_shoulder, nose)
        
        return angles
