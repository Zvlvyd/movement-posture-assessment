"""
处方生成模块 v2 Pydantic 请求/响应模型。
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ── 请求模型 ────────────────────────────

class GenerateRequest(BaseModel):
    """生成处方请求。"""
    assessment_record_id: int = Field(..., description="体态评估记录 ID")
    fms_record_id: int = Field(..., description="FMS 筛查记录 ID")
    user_level: int = Field(default=1, ge=1, le=5, description="训练水平 1-5")
    force_local: bool = Field(default=False, description="强制使用本地引擎（跳过 DeepSeek）")


class ActivateRequest(BaseModel):
    """激活处方请求。"""
    pass  # 无需额外参数


# ── 响应模型 ────────────────────────────

class PlanItemResponse(BaseModel):
    """处方计划项响应。"""
    id: int
    plan_id: int
    action_id: str
    action_name: str
    family_name: Optional[str] = None
    category: Optional[str] = None
    phase: str
    sets: int
    reps: int
    duration_seconds: int
    order_index: int
    difficulty: int
    intensity: str
    notes: Optional[str] = None
    is_substitution: bool = False
    # 教学信息
    steps: Optional[List[str]] = None
    cues: Optional[List[str]] = None
    display_type: Optional[str] = "image"
    display_url: Optional[str] = ""

    class Config:
        from_attributes = True


class PlanResponse(BaseModel):
    """处方计划响应。"""
    id: int
    user_id: int
    assessment_record_id: Optional[int] = None
    fms_record_id: Optional[int] = None
    plan_name: str
    overall_strategy: Optional[str] = None
    status: str
    generation_method: str
    template_version: Optional[str] = None
    plan_meta: Optional[dict] = None
    created_at: Optional[str] = None
    activated_at: Optional[str] = None
    completed_at: Optional[str] = None
    items: List[PlanItemResponse] = []

    class Config:
        from_attributes = True


class PlanListResponse(BaseModel):
    """处方计划列表响应。"""
    plans: List[PlanResponse]
    total: int


class GenerateResponse(BaseModel):
    """生成处方响应。"""
    success: bool
    plan: Optional[PlanResponse] = None
    generation_method: str = ""
    error_message: str = ""
    fallback_used: bool = False


class ActivateResponse(BaseModel):
    """激活处方响应。"""
    success: bool
    message: str
    bridge_prescription_id: Optional[int] = None  # 兼容旧训练页面的桥接 ID


class ActionLibraryItemResponse(BaseModel):
    """动作库条目响应。"""
    id: str
    family: str
    family_name: str
    name: str
    category: str
    subcategory: str
    difficulty: int
    intensity: str
    target_body_parts: List[str]
    phases: List[str]
    default_sets: int
    default_reps: int
    default_duration_seconds: int
    description: str
    steps: List[str]
    cues: List[str]
    display_type: str
    display_url: str
    is_visible: Optional[bool] = True


class ActionLibraryResponse(BaseModel):
    """动作库列表响应。"""
    actions: List[ActionLibraryItemResponse]
    total: int
    families: List[dict]
