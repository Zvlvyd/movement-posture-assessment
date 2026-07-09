# -*- coding: utf-8 -*-
"""
评估模块 - 基于关节角度分析的体态评估
"""
from .movement_definitions import (
    MovementDefinition, MovementSide, JointTarget,
    MOVEMENTS, get_movement, get_all_movements, get_target_angle_keys,
)
from .rom_tracker import ROMTracker, JointROM, MovementROMResult
from .asymmetry_analyzer import AsymmetryAnalyzer, AsymmetryFinding
from .scoring import UnifiedScoringEngine, DimensionScore
from .report_generator import ReportGenerator, UnifiedAssessmentReport
from .multi_view_analyzer import MultiViewAnalyzer, MergedPostureFindings, StaticFinding, ViewKeypoints
from .velocity_analyzer import VelocityAnalyzer, VelocityAsymmetryFinding, VelocityProfile
from .verification_mapper import VerificationMapper, VerificationMovement, VERIFICATION_MAP
from .fusion_engine import FusionEngine, FusionResult, FindingValidation

__all__ = [
    'MovementDefinition', 'MovementSide', 'JointTarget',
    'MOVEMENTS', 'get_movement', 'get_all_movements', 'get_target_angle_keys',
    'ROMTracker', 'JointROM', 'MovementROMResult',
    'AsymmetryAnalyzer', 'AsymmetryFinding',
    'UnifiedScoringEngine', 'DimensionScore',
    'ReportGenerator', 'UnifiedAssessmentReport',
    'MultiViewAnalyzer', 'MergedPostureFindings', 'StaticFinding', 'ViewKeypoints',
    'VelocityAnalyzer', 'VelocityAsymmetryFinding', 'VelocityProfile',
    'VerificationMapper', 'VerificationMovement', 'VERIFICATION_MAP',
    'FusionEngine', 'FusionResult', 'FindingValidation',
]
