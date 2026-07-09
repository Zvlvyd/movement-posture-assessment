# -*- coding: utf-8 -*-
"""Pydantic schemas for student class operations (join / list / leave)."""
from pydantic import BaseModel, Field
from typing import Optional, List


class JoinClassRequest(BaseModel):
    invite_code: str = Field(..., min_length=8, max_length=8, description="8位班级邀请码")


class CoachBriefResponse(BaseModel):
    id: int
    username: str
    phone: Optional[str] = None


class MyClassResponse(BaseModel):
    class_id: int
    class_name: str
    description: Optional[str] = None
    invite_code: Optional[str] = None
    coach: CoachBriefResponse
    student_count: int
    created_at: str


class MyClassListResponse(BaseModel):
    classes: List[MyClassResponse]


class JoinClassResponse(BaseModel):
    message: str
    class_info: MyClassResponse


class LeaveClassResponse(BaseModel):
    message: str


class RegenerateCodeResponse(BaseModel):
    invite_code: str
    message: str
