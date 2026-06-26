# -*- coding: utf-8 -*-
"""Business services — authentication, assessment, training, and reporting logic."""
from .auth_service import register_user, login_user, get_current_user, require_role
from .assessment_service import (
    AssessmentService, RealtimeAssessmentService, VerificationWebSocketHandler,
)
from .fms_service import FMSService, RealtimeFMSService
from .prescription_service import PrescriptionService
from .training_service import TrainingService, TrainingWebSocketHandler
from .learning_service import LearningService, RealtimeLearningService
from .report_service import ReportService, RetestService, CycleService, BadgeService
from .base import BaseWebSocketHandler
__all__ = [
    "register_user", "login_user", "get_current_user", "require_role",
    "AssessmentService", "RealtimeAssessmentService", "VerificationWebSocketHandler",
    "FMSService", "RealtimeFMSService", "PrescriptionService",
    "TrainingService", "TrainingWebSocketHandler",
    "LearningService", "RealtimeLearningService",
    "ReportService", "RetestService", "CycleService", "BadgeService",
    "BaseWebSocketHandler",
]
