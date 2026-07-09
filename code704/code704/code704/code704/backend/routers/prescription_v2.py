"""
处方生成模块 v2 API 路由。

端点：
- POST /api/prescription-v2/generate     生成处方计划
- GET  /api/prescription-v2/plans        获取计划列表
- GET  /api/prescription-v2/plans/{id}   获取计划详情
- POST /api/prescription-v2/plans/{id}/activate  激活计划
- GET  /api/prescription-v2/actions      获取完整动作库
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.services.auth_service import get_current_user
from backend.database.models import User, AssessmentRecord, FMSRecord, RiskLevel
from backend.schemas.prescription_v2 import (
    GenerateRequest, GenerateResponse,
    PlanResponse, PlanListResponse,
    ActivateResponse, ActionLibraryResponse,
)
from backend.services.prescription_v2_service import PrescriptionV2Service

router = APIRouter(prefix="/api/prescription-v2", tags=["prescription-v2"])

# 服务实例（模块级单例）
_service = PrescriptionV2Service()


@router.post("/generate", response_model=GenerateResponse)
async def generate_prescription(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """生成训练处方计划。

    优先使用 DeepSeek AI 生成，失败时自动回退本地规则引擎。
    设置 force_local=true 可强制使用本地引擎。
    """
    result = await _service.generate(
        db=db,
        user_id=current_user.id,
        assessment_record_id=req.assessment_record_id,
        fms_record_id=req.fms_record_id,
        user_level=req.user_level,
        force_local=req.force_local,
        training_goal=req.training_goal,
        training_duration=req.training_duration,
        training_frequency=req.training_frequency,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error_message"])

    return GenerateResponse(
        success=True,
        plan=PlanResponse(**result["plan"]) if result["plan"] else None,
        generation_method=result["generation_method"],
        error_message=result.get("error_message", ""),
        fallback_used=result.get("fallback_used", False),
    )


@router.get("/plans", response_model=PlanListResponse)
def list_plans(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的所有处方计划。"""
    plans = _service.list_plans(db, current_user.id)
    return PlanListResponse(
        plans=[PlanResponse(**p) for p in plans],
        total=len(plans),
    )


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取单个处方计划详情。"""
    plan = _service.get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")
    return PlanResponse(**plan)


@router.post("/plans/{plan_id}/activate", response_model=ActivateResponse)
def activate_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """激活处方计划。

    激活后可用 bridge_prescription_id 跳转到现有训练页面开始训练。
    """
    result = _service.activate_plan(db, plan_id, current_user.id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return ActivateResponse(**result)


@router.delete("/plans/{plan_id}")
def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """删除训练计划（仅允许删除非激活状态的计划）"""
    svc = PrescriptionV2Service()
    try:
        ok = svc.delete_plan(db, plan_id, current_user.id)
        if not ok:
            raise HTTPException(status_code=404, detail="计划不存在")
        return {"success": True, "message": "计划已删除"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Plan Edit (new) ──────────────────────────────────────────────────

from typing import Optional
from pydantic import BaseModel as PydanticBaseModel

class _PlanEditBody(PydanticBaseModel):
    plan_name: Optional[str] = None
    overall_strategy: Optional[str] = None
    items: Optional[list] = None
    student_notes: Optional[str] = None

class _PlanSubmitBody(PydanticBaseModel):
    student_notes: str = ''


@router.put("/plans/{plan_id}", summary="修改训练计划")
def edit_plan(
    plan_id: int,
    body: _PlanEditBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改计划。无班级直接生效，有班级创建审批请求"""
    from backend.services import plan_edit_service
    return plan_edit_service.edit_plan(db, current_user, plan_id, body.model_dump(exclude_none=True))


@router.post("/plans/{plan_id}/submit-change", summary="提交计划变更给教练审批")
def submit_change_request(
    plan_id: int,
    body: _PlanSubmitBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """显式提交计划变更给教练审批"""
    from backend.services import plan_edit_service
    return plan_edit_service.submit_change_request(db, current_user, plan_id, body.student_notes)


@router.get("/change-requests", summary="查看自己的变更请求")
def list_my_change_requests(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from backend.services import plan_edit_service
    return plan_edit_service.list_my_change_requests(db, current_user)


@router.get("/actions", response_model=ActionLibraryResponse)
def get_actions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取完整标准动作库（排除隐藏动作）。"""
    data = _service.get_action_library(db)
    return ActionLibraryResponse(**data)


# ── 训练进度端点 ──────────────────────────

from backend.database.models_v2 import TrainingCompletion, PrescriptionPlanItem
from pydantic import BaseModel


class SaveProgressRequest(BaseModel):
    plan_id: int
    plan_item_id: int
    action_name: str
    best_score: float = 0
    rep_count: int = 0
    hold_time_seconds: float = 0
    duration_seconds: float = 0


class ItemProgress(BaseModel):
    plan_item_id: int
    sets_done: int          # 已完成的组数
    total_sets: int         # 目标组数
    latest_reps: int = 0    # 最近一组完成的次数
    latest_score: float = 0 # 最近一组的最佳得分


class PlanProgressResponse(BaseModel):
    plan_id: int
    items: list[ItemProgress]
    completed_item_ids: list[int]  # 全部组完成的 plan_item_id
    total_items: int


@router.post("/progress", response_model=dict)
def save_progress(
    req: SaveProgressRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """保存训练完成记录。每次练完一个动作（一组）调用此接口。"""
    record = TrainingCompletion(
        user_id=current_user.id,
        plan_id=req.plan_id,
        plan_item_id=req.plan_item_id,
        action_name=req.action_name,
        best_score=req.best_score,
        rep_count=req.rep_count,
        hold_time_seconds=req.hold_time_seconds,
        duration_seconds=req.duration_seconds,
    )
    db.add(record)
    db.commit()
    return {"success": True, "record_id": record.id}


@router.get("/plans/{plan_id}/progress", response_model=PlanProgressResponse)
def get_plan_progress(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询某个计划的训练进度，包含每组完成详情。"""
    items = db.query(PrescriptionPlanItem).filter(
        PrescriptionPlanItem.plan_id == plan_id
    ).all()

    completions = db.query(TrainingCompletion).filter(
        TrainingCompletion.user_id == current_user.id,
        TrainingCompletion.plan_id == plan_id,
    ).order_by(TrainingCompletion.created_at.asc()).all()

    # 按 plan_item_id 分组
    from collections import defaultdict
    by_item = defaultdict(list)
    for c in completions:
        by_item[c.plan_item_id].append(c)

    item_progresses = []
    all_done_ids = []

    for item in items:
        records = by_item.get(item.id, [])
        latest = records[-1] if records else None

        # 累加模式下统计完成组数：reps 优先（次数类），否则按训练次数（计时类）
        if item.reps and item.reps > 0:
            total_reps = sum(r.rep_count for r in records)
            sets_done = total_reps // max(item.reps, 1)
            partial_reps = total_reps % max(item.reps, 1)
        elif item.duration_seconds > 0:
            # 计时类动作：每完成一次训练 = 一组
            sets_done = len(records)
            partial_reps = 0
        else:
            # 没有明确目标的动作，每次训练算一组
            sets_done = len(records)
            partial_reps = 0

        # 全部组完成
        if sets_done >= item.sets:
            all_done_ids.append(item.id)

        item_progresses.append(ItemProgress(
            plan_item_id=item.id,
            sets_done=min(sets_done, item.sets),
            total_sets=item.sets,
            latest_reps=partial_reps if sets_done < item.sets else 0,
            latest_score=latest.best_score if latest else 0,
        ))

    return PlanProgressResponse(
        plan_id=plan_id,
        items=item_progresses,
        completed_item_ids=all_done_ids,
        total_items=len(items),
    )


# ── 测试辅助端点 ──────────────────────────

from datetime import datetime
import json


def _require_test_endpoints():
    """If test endpoints are disabled, return 404 (hide their existence)."""
    if not settings.ENABLE_TEST_ENDPOINTS:
        raise HTTPException(status_code=404, detail="Not Found")


class MockAssessmentRequest(BaseModel):
    problems: list[str] = []          # 检测到的问题 flag 列表
    severities: dict[str, str] = {}   # {flag: "mild"|"moderate"|"severe"}


class MockFMSRequest(BaseModel):
    balance_score: float = 55
    flexibility_score: float = 55
    upper_limb_score: float = 60
    core_score: float = 50
    symmetry_score: float = 55


class MockBothRequest(BaseModel):
    assessment: MockAssessmentRequest
    fms: MockFMSRequest


@router.post("/test/mock-assessment")
def create_mock_assessment(
    req: MockAssessmentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _enabled=Depends(_require_test_endpoints),
):
    """创建模拟体态评估记录，返回记录 ID。"""
    # 构造 severity weights
    sev_weight = {"mild": 0.4, "moderate": 0.7, "severe": 1.0}
    problems_detail = []
    for flag in req.problems:
        severity = req.severities.get(flag, "mild")
        problems_detail.append({
            "flag": flag,
            "severity": severity,
            "weight": sev_weight.get(severity, 0.5),
        })

    # 构造兼容 PostureAnalyzer 格式的 posture_data
    flags = [p["flag"] for p in problems_detail]
    measurements = {}
    for p in problems_detail:
        if p["flag"] == "head_forward_posture":
            measurements["head_forward_deg"] = 22 if p["severity"] == "moderate" else 17
        elif p["flag"] == "shoulder_imbalance":
            measurements["shoulder_height_diff_px"] = 25 if p["severity"] == "moderate" else 14
        elif p["flag"] == "pelvic_lateral_tilt":
            measurements["hip_height_diff_px"] = 25 if p["severity"] == "moderate" else 14
        elif p["flag"] == "knee_hyperextension":
            measurements["knee_hyperextension_deg"] = -10 if p["severity"] == "moderate" else -6
        elif p["flag"] in ("pelvic_anterior_tilt", "pelvic_posterior_tilt"):
            measurements["pelvic_forward_offset_px"] = 40 if p["severity"] == "moderate" else 25

    posture_data = {
        "flags": flags,
        "problems": problems_detail,
        "measurements": measurements,
    }

    # 构造肌肉分析
    muscle_map = {
        "head_forward_posture": {"tight": ["胸锁乳突肌", "胸小肌"], "weak": ["深层颈屈肌", "下斜方肌", "菱形肌"]},
        "shoulder_imbalance": {"tight": ["斜方肌上束"], "weak": ["下斜方肌", "前锯肌"]},
        "pelvic_lateral_tilt": {"tight": ["腰方肌"], "weak": ["臀中肌"]},
        "knee_hyperextension": {"tight": ["腘绳肌"], "weak": ["股四头肌", "臀中肌", "臀大肌"]},
        "pelvic_anterior_tilt": {"tight": ["髂腰肌", "股直肌"], "weak": ["臀大肌", "腹横肌", "腘绳肌"]},
        "pelvic_posterior_tilt": {"tight": ["腘绳肌", "臀大肌"], "weak": ["髂腰肌", "股直肌", "竖脊肌"]},
    }
    tight = set()
    weak = set()
    for flag in flags:
        m = muscle_map.get(flag, {})
        tight.update(m.get("tight", []))
        weak.update(m.get("weak", []))
    muscle_findings = {"tight_muscles": list(tight), "weak_muscles": list(weak)}

    # 计算模拟分数
    n = len(flags)
    overall = max(20, 100 - n * 12)
    dim = max(25, 100 - n * 15)
    risk = "high" if overall < 40 else "medium" if overall < 60 else "low"

    record = AssessmentRecord(
        user_id=current_user.id,
        test_date=datetime.utcnow(),
        balance_score=dim, flexibility_score=dim,
        upper_limb_score=dim, core_score=dim, symmetry_score=dim,
        overall_score=overall,
        risk_level=RiskLevel(risk),
        posture_data=json.dumps(posture_data, ensure_ascii=False),
        muscle_findings=json.dumps(muscle_findings, ensure_ascii=False),
        movement_data=json.dumps({"rom_data": {}, "asymmetry_findings": []}, ensure_ascii=False),
        rom_data=json.dumps({}, ensure_ascii=False),
        assessment_type="mock_test",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "record_id": record.id, "overall_score": overall, "risk_level": risk}


@router.post("/test/mock-fms")
def create_mock_fms(
    req: MockFMSRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _enabled=Depends(_require_test_endpoints),
):
    """创建模拟 FMS 筛查记录，返回记录 ID。"""
    scores = [
        req.balance_score, req.flexibility_score,
        req.upper_limb_score, req.core_score, req.symmetry_score,
    ]
    overall = sum(scores) / len(scores)
    risk = "low" if overall >= 80 else "medium" if overall >= 60 else "high"

    record = FMSRecord(
        user_id=current_user.id,
        test_date=datetime.utcnow(),
        balance_score=req.balance_score,
        flexibility_score=req.flexibility_score,
        upper_limb_score=req.upper_limb_score,
        core_score=req.core_score,
        symmetry_score=req.symmetry_score,
        overall_score=round(overall, 1),
        risk_level=RiskLevel(risk),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"success": True, "record_id": record.id, "overall_score": round(overall, 1), "risk_level": risk}


@router.post("/test/mock-both")
def create_mock_both(
    req: MockBothRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    _enabled=Depends(_require_test_endpoints),
):
    """同时创建模拟体态评估和 FMS 记录，返回两个 ID。"""
    ar = create_mock_assessment(req.assessment, current_user, db)
    fr = create_mock_fms(req.fms, current_user, db)
    return {
        "success": True,
        "assessment_record_id": ar["record_id"],
        "fms_record_id": fr["record_id"],
        "assessment_overall": ar["overall_score"],
        "fms_overall": fr["overall_score"],
    }
