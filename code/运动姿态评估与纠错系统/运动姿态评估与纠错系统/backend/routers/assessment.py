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
from backend.config import settings

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
    
    svc = RealtimeAssessmentService(db)
    try:
        await svc.handle_session(ws, user_id)
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": f"会话异常: {str(e)}"})
        except:
            pass


# ─── Periodic Re-test & Prescription Upgrade ────────────────────────────────
from datetime import timedelta
from backend.database import models as db_models
from models.prescription.recommendation_engine import PrescriptionEngine

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


