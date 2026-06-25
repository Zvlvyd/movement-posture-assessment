from typing import Dict, List, Tuple
from dataclasses import dataclass
import math

@dataclass
class FMSScore:
    dimension: str
    score: float
    max_score: float = 100.0
    label: str = ''

class FMSScoringEngine:
    DIMENSIONS = ['balance', 'flexibility', 'upper_limb', 'core', 'symmetry']
    
    DIMENSION_LABELS = {
        'balance': '平衡',
        'flexibility': '灵活性',
        'upper_limb': '上肢',
        'core': '核心',
        'symmetry': '对称性',
    }
    
    def score_balance(self, duration_seconds: float) -> FMSScore:
        if duration_seconds >= 30:
            score = 100.0
        else:
            score = max(0.0, 100.0 - (30.0 - duration_seconds) * 3.0)
        return FMSScore(dimension='balance', score=score, label='闭眼单腿站立')
    
    def score_flexibility(self, depth_angle: float, trunk_tilt: float, arm_maintained: float) -> FMSScore:
        depth_score = min(100.0, max(0.0, (180.0 - depth_angle) / 90.0 * 100.0))
        trunk_score = min(100.0, max(0.0, 100.0 - trunk_tilt * 2.0))
        arm_score = arm_maintained * 100.0
        score = depth_score * 0.5 + trunk_score * 0.3 + arm_score * 0.2
        return FMSScore(dimension='flexibility', score=score, label='过头深蹲')
    
    def score_upper_limb(self, hand_distance_cm: float) -> FMSScore:
        score = max(0.0, 100.0 - hand_distance_cm * 2.0)
        return FMSScore(dimension='upper_limb', score=score, label='肩关节活动度')
    
    def score_core(self, duration_seconds: float) -> FMSScore:
        score = min(100.0, duration_seconds / 60.0 * 100.0)
        return FMSScore(dimension='core', score=score, label='平板支撑')
    
    def score_symmetry(self, left_score: float, right_score: float) -> FMSScore:
        diff = abs(left_score - right_score)
        score = max(0.0, 100.0 - diff * 2.0)
        return FMSScore(dimension='symmetry', score=score, label='弓步蹲对称')
    
    def compute_overall(self, scores: List[FMSScore]) -> float:
        weights = {'balance': 0.2, 'flexibility': 0.25, 'upper_limb': 0.15, 'core': 0.2, 'symmetry': 0.2}
        total = sum(s.score * weights.get(s.dimension, 0.2) for s in scores)
        return round(total, 1)
    
    def get_risk_level(self, overall_score: float, scores: List[FMSScore]) -> str:
        if overall_score < 40 or any(s.score < 30 for s in scores):
            return 'high'
        elif overall_score < 70 or any(s.score < 50 for s in scores):
            return 'medium'
        return 'low'
