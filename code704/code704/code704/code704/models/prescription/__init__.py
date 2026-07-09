# -*- coding: utf-8 -*-
"""Prescription engine — AI exercise prescription and problem-exercise mapping."""
from .recommendation_engine import PrescriptionEngine
from .problem_exercise_mapper import PosturePrescriptionBuilder
__all__ = ["PrescriptionEngine", "PosturePrescriptionBuilder"]
