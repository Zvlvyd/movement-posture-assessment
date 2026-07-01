"""
处方生成模块 v2 API 路由。

端点：
- POST /api/prescription-v2/generate     生成处方计划
- GET  /api/prescription-v2/plans        获取计划列表
- GET  /api/prescription-v2/plans/{id}   获取计划详情
- POST /api/prescription-v2/plans/{id}/activate  激活计划
- GET  /api/prescription-v2/actions      获取完整动作库
"""
from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.get("/actions", response_model=ActionLibraryResponse)
def get_actions(
    current_user: User = Depends(get_current_user),
):
    """获取完整标准动作库（无需数据库查询）。"""
    data = _service.get_action_library()
    return ActionLibraryResponse(**data)


# ── 测试辅助端点 ──────────────────────────

from pydantic import BaseModel
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
