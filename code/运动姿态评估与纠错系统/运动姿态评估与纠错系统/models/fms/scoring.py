# -*- coding: utf-8 -*-
"""FMS Scoring Engine - minimal compatible module"""
import math
from typing import List

class Score:
    def __init__(self, dimension: str, score_val: float, detail: str = ""):
        self.dimension = dimension
        self.score = round(score_val, 1)
        self.detail = detail

class FMSScoringEngine:
    DIMENSION_WEIGHTS = {"balance": 0.2, "flexibility": 0.25, "upper_limb": 0.15, "core": 0.2, "symmetry": 0.2}
    
    def score_balance(self, duration_sec):
        s = min(100, max(0, duration_sec / 60.0 * 100))
        return Score("balance", s, f"单腿站立 {duration_sec:.1f}s")
    
    def score_flexibility(self, depth_cm, trunk_angle, arm_ratio):
        s = min(100, max(0, depth_cm / 20.0 * 50 + (1.0 - abs(trunk_angle) / 30.0) * 50 + arm_ratio * 20))
        return Score("flexibility", s, f"体前屈 {depth_cm:.1f}cm")
    
    def score_upper_limb(self, distance_cm):
        s = min(100, max(0, (1.0 - distance_cm / 20.0) * 100))
        return Score("upper_limb", s, f"背后触肩距 {distance_cm:.1f}cm")
    
    def score_core(self, duration_sec):
        s = min(100, max(0, duration_sec / 120.0 * 100))
        return Score("core", s, f"平板支撑 {duration_sec:.1f}s")
    
    def score_symmetry(self, left, right):
        diff = abs(left - right)
        total = (left + right) / 2.0
        ratio = diff / max(total, 0.01)
        s = max(0, 100 - ratio * 100)
        return Score("symmetry", s, f"左右差 {diff:.1f}")
    
    def compute_overall(self, scores):
        if not scores: return 50.0
        total = sum(s.score * self.DIMENSION_WEIGHTS.get(s.dimension, 0.2) for s in scores)
        wsum = sum(self.DIMENSION_WEIGHTS.get(s.dimension, 0.2) for s in scores)
        return round(total / max(wsum, 0.01), 1)
    
    def get_risk_level(self, overall, scores):
        if overall >= 80: return "低风险"
        if overall >= 60: return "中风险"
        if overall >= 40: return "高风险"
        return "极高风险"