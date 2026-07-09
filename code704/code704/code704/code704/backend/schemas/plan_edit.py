# -*- coding: utf-8 -*-
"""Pydantic schemas for plan edit / change request / approval workflow."""
from pydantic import BaseModel, Field
from typing import Optional, List


# ── Plan Item Edit ────────────────────────────────────────────────

class PlanItemEdit(BaseModel):
    """Single plan item fields that can be edited."""
    action_name: Optional[str] = None
    sets: Optional[int] = None
    reps: Optional[int] = None
    duration_seconds: Optional[int] = None
    difficulty: Optional[int] = None
    intensity: Optional[str] = None
    notes: Optional[str] = None


class PlanEditRequest(BaseModel):
    """Request to edit a plan — can include full item list or partial changes."""
    plan_name: Optional[str] = None
    overall_strategy: Optional[str] = None
    items: Optional[List[dict]] = None  # Full proposed item list
    student_notes: Optional[str] = None


class PlanSubmitRequest(BaseModel):
    """Explicitly submit plan changes for coach approval."""
    student_notes: Optional[str] = None


# ── Change Request ────────────────────────────────────────────────

class ChangeRequestResponse(BaseModel):
    id: int
    plan_id: int
    plan_name: str = ""
    student_id: int
    student_name: str = ""
    coach_id: Optional[int] = None
    status: str
    original_snapshot: Optional[str] = None
    proposed_items: Optional[str] = None
    coach_items: Optional[str] = None
    coach_notes: Optional[str] = None
    student_notes: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class ChangeRequestListResponse(BaseModel):
    requests: List[ChangeRequestResponse]
    total: int


# ── Coach Approval ─────────────────────────────────────────────────

class CoachApproveRequest(BaseModel):
    pass  # No body needed for simple approve


class CoachAdjustRequest(BaseModel):
    items: List[dict]  # Coach-adjusted item list
    coach_notes: Optional[str] = None


class CoachRejectRequest(BaseModel):
    coach_notes: str = Field(..., min_length=1, description="拒绝原因不能为空")
