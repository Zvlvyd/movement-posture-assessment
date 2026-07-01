# -*- coding: utf-8 -*-
"""
评估路由 - 替代 routers/fms.py
POST /api/assessment/submit   - 提交关键点数据，返回评估结果
GET  /api/assessment/records  - 历史记录列表
GET  /api/assessment/records/{id} - 单条详情
WS   /api/assessment/ws       - 实时评估 WebSocket
"""
from fastapi import APIRouter, Depends, WebSocket, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.schemas.business import (
    AssessmentSubmitRequest, AssessmentResponse, AssessmentListResponse,
)
from backend.services.assessment_service import AssessmentService, RealtimeAssessmentService
from backend.services.auth_service import get_current_user
from backend.database.models import User, AssessmentRecord
from jose import jwt as jose_jwt
from config.settings import settings
from backend.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/assessment", tags=["Assessment"])


@router.post("/submit", response_model=AssessmentResponse)
def submit_assessment(
    data: AssessmentSubmitRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """提交姿态数据，运行评估管道，返回并存储结果"""
    svc = AssessmentService(db)
    record = svc.submit_assessment(
        user_id=user.id,
        keypoints_front=data.keypoints_front,
        keypoints_side=data.keypoints_side,
        movement_frames=data.movement_frames,
    )
    return svc.build_detail_response(record)


@router.get("/records", response_model=List[AssessmentListResponse])
def get_records(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取用户所有评估记录（列表视图，不含展开数据）"""
    svc = AssessmentService(db)
    records = svc.get_user_records(user.id)
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "test_date": r.test_date,
            "balance_score": r.balance_score,
            "flexibility_score": r.flexibility_score,
            "upper_limb_score": r.upper_limb_score,
            "core_score": r.core_score,
            "symmetry_score": r.symmetry_score,
            "overall_score": r.overall_score,
            "risk_level": r.risk_level,
        }
        for r in records
    ]


@router.get("/records/{record_id}")
def get_record_detail(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单条评估详情（含完整报告数据）"""
    svc = AssessmentService(db)
    record = svc.get_record_detail(record_id, user.id)
    return svc.build_detail_response(record)


@router.post("/records/{record_id}/generate-report")
async def generate_ai_report(
    record_id: int,
    regenerate: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """调用 DeepSeek AI 生成体态评估报告。设 regenerate=true 强制重新生成。"""
    import json as _json

    svc = AssessmentService(db)
    record = svc.get_record_detail(record_id, user.id)

    # 解析已有 report_data
    report_data = record.report_data
    if isinstance(report_data, str):
        try:
            report_data = _json.loads(report_data)
        except (_json.JSONDecodeError, TypeError):
            report_data = {}
    if not report_data:
        report_data = {}

    # 有缓存且不强制重新生成 → 直接返回
    if not regenerate and report_data.get("ai_report"):
        return {"report": report_data["ai_report"], "cached": True}

    # 调用 DeepSeek 生成
    from backend.services.deepseek_service import generate_assessment_report

    assessment_dict = {
        "balance_score": record.balance_score,
        "flexibility_score": record.flexibility_score,
        "upper_limb_score": record.upper_limb_score,
        "core_score": record.core_score,
        "symmetry_score": record.symmetry_score,
        "overall_score": record.overall_score,
        "risk_level": record.risk_level.value if record.risk_level else None,
        "posture_data": record.posture_data,
        "muscle_findings": record.muscle_findings,
        "rom_data": record.rom_data,
        "movement_data": record.movement_data,
    }

    try:
        report_text = await generate_assessment_report(assessment_dict)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("AI 报告生成异常")
        raise HTTPException(status_code=500, detail=f"AI 报告生成异常: {str(e)}")

    # 缓存到 report_data
    report_data["ai_report"] = report_text
    record.report_data = _json.dumps(report_data, ensure_ascii=False)
    db.commit()

    return {"report": report_text, "cached": False}


@router.delete("/records/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除指定评估记录"""
    svc = AssessmentService(db)
    try:
        svc.delete_record(record_id, user.id)
        return {"success": True, "message": "评估记录已删除"}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("删除评估记录异常")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.websocket("/ws")
async def assessment_websocket(
    ws: WebSocket,
    db: Session = Depends(get_db),
):
    """实时评估 WebSocket
    先 accept 再验证 token，避免浏览器端收到 HTTP 403 导致 onerror。
    """
    await ws.accept()
    
    token = ws.query_params.get("token")
    if not token:
        await ws.send_json({"type": "error", "message": "缺少认证令牌"})
        await ws.close(code=4001)
        return
    
    try:
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await ws.send_json({"type": "error", "message": "用户不存在"})
            await ws.close(code=4003)
            return
    except Exception:
        await ws.send_json({"type": "error", "message": "令牌无效或已过期"})
        await ws.close(code=4001)
        return
    
    # Check if this is a verification-mode session
    verification_mode = ws.query_params.get("verification_mode", "false").lower() == "true"

    if verification_mode:
        from backend.services.assessment_service import VerificationWebSocketHandler
        svc = VerificationWebSocketHandler(db)
    else:
        svc = RealtimeAssessmentService(db)

    try:
        await svc.handle(ws, user_id)
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": f"会话异常: {str(e)}"})
        except:
            pass


# ─── Periodic Re-test & Prescription Upgrade ────────────────────────────────

@router.get("/re-test-status")
def get_re_test_status(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Check if the user is due for a periodic re-test."""
    svc = AssessmentService(db)
    return svc.check_re_test_status(user.id)

@router.post("/trigger-re-test")
def trigger_re_test(
    prescription_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """User requests a periodic re-test: marks current phase complete and unlocks next."""
    svc = AssessmentService(db)
    return svc.trigger_phase_upgrade(user.id, prescription_id)


