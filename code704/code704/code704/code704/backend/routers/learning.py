# -*- coding: utf-8 -*-
"""
学习路由 - 标准动作库 + 标准学习模式 WebSocket
GET  /api/learning/actions           - 动作库列表（原有）
GET  /api/learning/actions/{id}       - 动作详情（原有）
GET  /api/learning/learnable          - 可标准学习的动作列表（新）
GET  /api/learning/learnable/{name}   - 动作标准角度详情（新）
WS   /api/learning/ws                 - 实时学习对比 WebSocket（新）
"""
import json

from fastapi import APIRouter, Depends, WebSocket, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.database.connection import get_db
from backend.database import models
from backend.schemas.business import ActionLibraryResponse
from backend.services.auth_service import get_current_user
from backend.services.learning_service import LearningService, RealtimeLearningService, UnifiedActionLoader
from backend.database.models import User
from jose import jwt as jose_jwt
from config.settings import settings

router = APIRouter(prefix='/api/learning', tags=['Learning'])


# ==============================
# 原有：动作库 CRUD
# ==============================

@router.get('/actions', response_model=List[ActionLibraryResponse])
def list_actions(
    category: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(models.ActionLibrary).filter(models.ActionLibrary.is_visible == True)
    if category:
        q = q.filter(models.ActionLibrary.category == category)
    return [ActionLibraryResponse.model_validate(a) for a in q.all()]


@router.get('/actions/{action_id}', response_model=ActionLibraryResponse)
def get_action(
    action_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    action = db.query(models.ActionLibrary).filter(models.ActionLibrary.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail='Action not found')
    return ActionLibraryResponse.model_validate(action)


# ==============================
# 新增：标准学习模式
# ==============================

@router.get('/learnable')
def list_learnable_actions(
    db: Session = Depends(get_db),
):
    """列出所有支持标准学习模式的动作（含 DB 中教练编辑的媒体和描述）"""
    svc = LearningService(db)
    return svc.list_learnable_actions()


@router.get('/learnable/{name}')
def get_learnable_action(
    name: str,
    db: Session = Depends(get_db),
):
    """获取指定动作的标准学习数据（含标准角度、常见错误、DB 中的媒体和描述）"""
    svc = LearningService(db)
    detail = svc.get_action_detail(name)
    if not detail:
        raise HTTPException(status_code=404, detail=f'未找到可学习的动作: {name}')
    return detail


@router.get('/views/{name}')
def get_action_views(name: str):
    """获取动作支持的观察视角列表"""
    loader = UnifiedActionLoader()
    action = loader.get_by_name(name)
    if not action:
        raise HTTPException(status_code=404, detail=f'未找到动作: {name}')
    return {
        "name": name,
        "views": action.get("views", ["正面"]),
    }


@router.get('/stats')
def get_learning_stats(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """标准学习训练统计"""
    from datetime import datetime, timedelta
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    base = db.query(models.AssessmentRecord).filter(
        models.AssessmentRecord.user_id == user.id,
        models.AssessmentRecord.assessment_type == 'learning'
    )
    total = base.count()
    week_count = base.filter(models.AssessmentRecord.test_date >= week_ago).count()
    month_count = base.filter(models.AssessmentRecord.test_date >= month_ago).count()
    avg_score = db.query(models.AssessmentRecord.overall_score).filter(
        models.AssessmentRecord.user_id == user.id,
        models.AssessmentRecord.assessment_type == 'learning'
    ).order_by(models.AssessmentRecord.test_date.desc()).limit(20).all()
    avg = round(sum(s[0] for s in avg_score if s[0]) / max(len([s for s in avg_score if s[0]]), 1), 1) if avg_score else 0
    return {
        "total_sessions": total,
        "total_sessions_7d": week_count,
        "total_sessions_30d": month_count,
        "average_score": avg,
        "current_streak": 0,
    }


@router.get('/records')
def get_learning_records(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的标准学习训练记录列表"""
    records = db.query(models.AssessmentRecord).filter(
        models.AssessmentRecord.user_id == user.id,
        models.AssessmentRecord.assessment_type == 'learning'
    ).order_by(models.AssessmentRecord.test_date.desc()).limit(50).all()
    from backend.services.learning_service import UnifiedActionLoader
    loader = UnifiedActionLoader()
    result = []
    for r in records:
        report_data = json.loads(r.report_data) if isinstance(r.report_data, str) else (r.report_data or {})
        posture_data = json.loads(r.posture_data) if isinstance(r.posture_data, str) else (r.posture_data or {})
        action_name = posture_data.get("action", "") if isinstance(posture_data, dict) else ""
        category = ""
        if action_name:
            merged = loader.get_merged_action(action_name)
            if merged:
                category = merged.get("category", "")
        result.append({
            "id": r.id,
            "action_name": action_name,
            "category": category,
            "overall_score": r.overall_score or 0,
            "total_score": r.overall_score or 0,
            "best_score": report_data.get("best_score", 0) if isinstance(report_data, dict) else 0,
            "duration": report_data.get("duration", 0) if isinstance(report_data, dict) else 0,
            "mode": "standard_learning",
            "start_time": str(r.test_date) if r.test_date else "",
        })
    return result


@router.get('/reports/{record_id}')
def get_learning_report(record_id: int, db: Session = Depends(get_db)):
    """获取标准学习训练报告"""
    svc = LearningService(db)
    report = svc.get_report(record_id)
    if not report:
        raise HTTPException(status_code=404, detail='报告不存在')
    return report


@router.websocket('/ws')
async def learning_websocket(
    ws: WebSocket,
    db: Session = Depends(get_db),
):
    """标准学习实时对比 WebSocket
    客户端发送帧 → 服务端返回用户与标准动作的角度差异分析
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

    svc = RealtimeLearningService(db)
    try:
        await svc.handle_session(ws, user_id)
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": f"会话异常: {str(e)}"})
        except:
            pass
