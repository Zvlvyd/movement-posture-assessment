# -*- coding: utf-8 -*-
"""
Configuration package — centralized settings and constants.
"""
from .settings import settings, Settings
from .constants import (
    DIMENSION_WEIGHTS,
    SEVERITY_SCORE_MAP,
    VELOCITY_DEFAULTS,
    GUIDANCE_MAP,
    BADGE_DEFINITIONS,
    FMS_TEST_DEFINITIONS,
)

__all__ = [
    "settings",
    "Settings",
    "DIMENSION_WEIGHTS",
    "SEVERITY_SCORE_MAP",
    "VELOCITY_DEFAULTS",
    "GUIDANCE_MAP",
    "BADGE_DEFINITIONS",
    "FMS_TEST_DEFINITIONS",
]
