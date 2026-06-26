# -*- coding: utf-8 -*-
"""Radar Report - minimal compatible module"""
from typing import List, Dict

class RadarReport:
    @staticmethod
    def generate(scores, overall, risk_level):
        dimensions = []
        mapping = {"balance": "平衡", "flexibility": "灵活性", "upper_limb": "上肢", "core": "核心", "symmetry": "对称性"}
        for s in scores:
            dimensions.append({"name": mapping.get(s.dimension, s.dimension), "score": s.score, "detail": s.detail})
        return {"overall": overall, "risk_level": risk_level, "dimensions": dimensions}