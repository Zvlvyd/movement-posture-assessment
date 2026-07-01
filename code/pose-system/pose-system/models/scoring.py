from typing import Dict, List, Optional, Tuple
from models.action_recognizer.action_definitions import get_action_definition, ActionDefinition

class DualModeScorer:
    @staticmethod
    def score_basic(angles, action_name):
        action_def = get_action_definition(action_name)
        warnings = []
        if angles.get('trunk_tilt') is not None:
            threshold = action_def.danger_thresholds.get('trunk_forward', 45.0)
            if angles['trunk_tilt'] > threshold:
                warnings.append({'type': 'danger', 'message': 'trunk forward lean excess', 'joint': 'trunk', 'severity': 'high'})
        left_knee = angles.get('left_knee')
        right_knee = angles.get('right_knee')
        if left_knee is not None and right_knee is not None:
            knee_diff = abs(left_knee - right_knee)
            threshold = action_def.danger_thresholds.get('knee_valgus', 15.0)
            if knee_diff > threshold:
                warnings.append({'type': 'danger', 'message': 'knee asymmetry detected', 'joint': 'knee', 'severity': 'high'})
        passed = len(warnings) == 0
        return {'mode': 'basic', 'passed': passed, 'result': 'pass' if passed else 'warning', 'warnings': warnings, 'action_name': action_name}

    @staticmethod
    def score_advanced(angles, action_name):
        action_def = get_action_definition(action_name)
        penalties = []
        total_points = 100.0
        joint_key = action_def.target_joint
        left_key = f'left_{joint_key}'
        right_key = f'right_{joint_key}'
        left_angle = angles.get(left_key)
        right_angle = angles.get(right_key)
        if left_angle is not None and left_angle < action_def.min_angle:
            diff = action_def.min_angle - left_angle
            penalty = min(20.0, diff * 0.5)
            total_points -= penalty
            penalties.append({'joint': left_key, 'deviation': diff, 'penalty': penalty, 'message': 'left ROM insufficient'})
        if right_angle is not None and right_angle < action_def.min_angle:
            diff = action_def.min_angle - right_angle
            penalty = min(20.0, diff * 0.5)
            total_points -= penalty
            penalties.append({'joint': right_key, 'deviation': diff, 'penalty': penalty, 'message': 'right ROM insufficient'})
        # Check max_angle for hyperextension
        if left_angle is not None and left_angle > action_def.max_angle:
            diff = left_angle - action_def.max_angle
            penalty = min(20.0, diff * 0.5)
            total_points -= penalty
            penalties.append({'joint': left_key, 'deviation': diff, 'penalty': penalty, 'message': 'left hyperextension'})
        if right_angle is not None and right_angle > action_def.max_angle:
            diff = right_angle - action_def.max_angle
            penalty = min(20.0, diff * 0.5)
            total_points -= penalty
            penalties.append({'joint': right_key, 'deviation': diff, 'penalty': penalty, 'message': 'right hyperextension'})
        if left_angle is not None and right_angle is not None:
            sym_diff = abs(left_angle - right_angle)
            sym_threshold = action_def.advanced_thresholds.get('depth_symmetry', 10.0)
            if sym_diff > sym_threshold:
                penalty = min(10.0, (sym_diff - sym_threshold) * 0.5)
                total_points -= penalty
                penalties.append({'joint': 'symmetry', 'deviation': sym_diff - sym_threshold, 'penalty': penalty, 'message': 'left-right asymmetry'})
        if angles.get('trunk_tilt') is not None:
            threshold = action_def.advanced_thresholds.get('trunk_forward', 30.0)
            if angles['trunk_tilt'] > threshold:
                diff = angles['trunk_tilt'] - threshold
                penalty = min(15.0, diff * 0.3)
                total_points -= penalty
                penalties.append({'joint': 'trunk', 'deviation': diff, 'penalty': penalty, 'message': 'trunk forward lean'})
        score = max(0.0, min(100.0, total_points))
        quality = 'excellent' if score >= 90 else 'good' if score >= 75 else 'fair' if score >= 60 else 'needs_improvement'
        return {'mode': 'advanced', 'score': round(score, 1), 'max_score': 100.0, 'penalties': penalties, 'action_name': action_name, 'quality': quality}
