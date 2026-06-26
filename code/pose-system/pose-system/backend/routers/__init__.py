# -*- coding: utf-8 -*-
"""API Routers — FastAPI route definitions."""
from .auth import router as auth_router
from .fms import router as fms_router
from .assessment import router as assessment_router
from .prescription import router as prescription_router
from .training import router as training_router
from .learning import router as learning_router
from .records import router as records_router
from .checkin import router as checkin_router
from .coach import router as coach_router
from .admin import router as admin_router
from .multi_view_assessment import router as multi_view_assessment_router
__all__ = [
    "auth_router", "fms_router", "assessment_router", "prescription_router",
    "training_router", "learning_router", "records_router", "checkin_router",
    "coach_router", "admin_router", "multi_view_assessment_router",
]
