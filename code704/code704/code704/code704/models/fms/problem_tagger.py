# -*- coding: utf-8 -*-
"""Problem Tagger - minimal compatible module"""
from typing import List

class ProblemTagger:
    @staticmethod
    def tag(scores):
        problems = []
        for s in scores:
            if s.score < 40:
                problems.append({"dimension": s.dimension, "severity": "高", "detail": s.detail})
            elif s.score < 60:
                problems.append({"dimension": s.dimension, "severity": "中", "detail": s.detail})
        return problems