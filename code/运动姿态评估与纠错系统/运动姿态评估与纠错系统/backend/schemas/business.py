from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel

# FMS
class FMSScoreItem(BaseModel):
    dimension: str
    label: str
    score: float

class FMSResultResponse(BaseModel):
    id: int
    user_id: int
    test_date: datetime
    balance_score: float
    flexibility_score: float
    upper_limb_score: float
    core_score: float
    symmetry_score: float
    overall_score: float
    risk_level: str
    radar_data: Optional[dict] = None
    problem_tags: Optional[List[dict]] = None

    class Config:
        from_attributes = True

class FMSSubmitRequest(BaseModel):
    balance_duration: Optional[float] = None
    flexibility_depth: Optional[float] = None
    flexibility_trunk: Optional[float] = None
    flexibility_arm: Optional[float] = None
    upper_limb_distance: Optional[float] = None
    core_duration: Optional[float] = None
    symmetry_left: Optional[float] = None
    symmetry_right: Optional[float] = None


# Assessment (new)
class AssessmentSubmitRequest(BaseModel):
    keypoints_front: List[List[float]]  # 正面关键点 (17,2)
    keypoints_side: Optional[List[List[float]]] = None  # 侧面关键点（可选）
    movement_frames: Optional[List[List[List[float]]]] = None  # 运动帧序列 [[kp_frame1], [kp_frame2], ...]


class JointROMItem(BaseModel):
    joint: str
    side: str
    rom_deg: float
    peak_angle: float
    min_angle: float
    plateau_detected: bool


class AsymmetryItem(BaseModel):
    joint: str
    side_limited: str
    rom_left: float
    rom_right: float
    diff_pct: float
    severity: str


class PostureProblemItem(BaseModel):
    flag: str
    name: str
    severity: str
    value: float
    normal_range: str = ""
    unit: str = ""
    cause: str = ""
    tight_muscles: List[dict] = []
    weak_muscles: List[dict] = []
    exercises: dict = {}


class MuscleAnalysisData(BaseModel):
    tight_muscles: List[dict] = []
    weak_muscles: List[dict] = []
    tight_count: int = 0
    weak_count: int = 0


class AssessmentResponse(BaseModel):
    id: int
    user_id: int
    test_date: datetime
    balance_score: float
    flexibility_score: float
    upper_limb_score: float
    core_score: float
    symmetry_score: float
    overall_score: float
    risk_level: str
    # Expanded data (loaded on demand)
    posture_problems: Optional[List[dict]] = None
    rom_analysis: Optional[List[dict]] = None
    asymmetry_findings: Optional[List[dict]] = None
    muscle_analysis: Optional[dict] = None
    chart_data: Optional[dict] = None
    suggestions: Optional[List[str]] = None
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class AssessmentListResponse(BaseModel):
    id: int
    user_id: int
    test_date: datetime
    balance_score: float
    flexibility_score: float
    upper_limb_score: float
    core_score: float
    symmetry_score: float
    overall_score: float
    risk_level: str

    class Config:
        from_attributes = True

# Prescription
class PrescriptionItemResponse(BaseModel):
    id: int
    action_name: str
    phase: str
    sets: int
    reps: int
    duration: int
    order_index: int
    difficulty: int
    description: Optional[str] = None

    class Config:
        from_attributes = True

class PrescriptionResponse(BaseModel):
    id: int
    user_id: int
    fms_record_id: int
    phase: int
    status: str
    difficulty: int
    created_at: datetime
    unlocked_at: Optional[datetime] = None
    items: List[PrescriptionItemResponse] = []

    class Config:
        from_attributes = True

# Training
class TrainingStartRequest(BaseModel):
    prescription_id: int
    mode: str = 'basic'

class TrainingRecordResponse(BaseModel):
    id: int
    user_id: int
    prescription_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    total_score: Optional[float] = None
    mode: str

    class Config:
        from_attributes = True

class TrainingSessionResponse(BaseModel):
    session_id: int
    score: Optional[float] = None
    quality: Optional[str] = None
    feedback: List[dict] = []

# Learning
class ActionLibraryResponse(BaseModel):
    id: int
    name: str
    category: str
    difficulty: int
    target_body_parts: Optional[str] = None
    description: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True
