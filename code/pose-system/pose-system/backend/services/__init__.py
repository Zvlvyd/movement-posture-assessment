# -*- coding: utf-8 -*-
"""Business services — authentication, assessment, training, and reporting logic."""
from .auth_service import register_user, login_user, get_current_user, require_role
from .assessment_service import (
    AssessmentService, RealtimeAssessmentService, VerificationWebSocketHandler,
)
from .fms_service import FMSService, RealtimeFMSService
from .prescription_service import PrescriptionService
from .learning_service import LearningService, RealtimeLearningService
from .report_service import ReportService, RetestService, CycleService, BadgeService
from .base import BaseWebSocketHandler
from .coach_service import (
    list_students, create_class, list_classes, add_student_to_class,
    get_class_stats, get_class_trend, get_coach_summary,
    search_available_trainees, get_student_profile,
)
from .admin_service import (
    list_users, change_role, toggle_status, get_system_config, get_logs,
)

__all__ = [
    "register_user", "login_user", "get_current_user", "require_role",
    "AssessmentService", "RealtimeAssessmentService", "VerificationWebSocketHandler",
    "FMSService", "RealtimeFMSService", "PrescriptionService",
    "LearningService", "RealtimeLearningService",
    "ReportService", "RetestService", "CycleService", "BadgeService",
    "BaseWebSocketHandler",
    # Coach service
    "list_students", "create_class", "list_classes", "add_student_to_class",
    "get_class_stats", "get_class_trend", "get_coach_summary",
    "search_available_trainees", "get_student_profile",
    # Admin service
    "list_users", "change_role", "toggle_status", "get_system_config", "get_logs",
]
