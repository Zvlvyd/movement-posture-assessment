# -*- coding: utf-8 -*-
"""
Coach Action Library Management Router
动作库管理 API — 教练可查看、编辑、新建动作，上传示例媒体
"""
import os
from fastapi import APIRouter, Depends, Query, UploadFile, File, Body
from sqlalchemy.orm import Session
from backend.database.connection import get_db
from backend.database.models import User, UserRole
from backend.services.auth_service import require_role
from backend.services import action_library_service

router = APIRouter(prefix='/api/coach', tags=['Coach Action Library'])

COACH_OR_ADMIN = (UserRole.COACH, UserRole.ADMIN)

# Upload directory — same as mounted in main.py
UPLOADS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads", "actions"
)


@router.get('/actions')
def list_actions(
    category: str = None,
    family: str = None,
    difficulty: int = None,
    body_part: str = None,
    search: str = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """列出合并后的标准动作库（DB + JSON + standard_actions）"""
    return action_library_service.get_merged_action_library(
        db, category, family, difficulty, body_part, search, page, page_size,
    )


@router.get('/actions/{action_id}')
def get_action(
    action_id: str,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """获取单个动作的统一详情（支持 DB id 或 JSON id/name）"""
    # Try as int first
    try:
        aid = int(action_id)
    except ValueError:
        aid = action_id
    return action_library_service.get_action_detail_unified(db, aid)


@router.put('/actions/{action_id}')
def update_action(
    action_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """更新动作元数据"""
    return action_library_service.update_action_metadata(db, action_id, data, coach)


@router.post('/actions')
def create_action(
    data: dict = Body(...),
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """创建自定义动作"""
    return action_library_service.create_custom_action(db, data, coach)


@router.post('/actions/{action_id}/upload-media')
def upload_action_media(
    action_id: int,
    file: UploadFile = File(...),
    media_type: str = Query('image', description='image / video / thumbnail'),
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """上传动作示例媒体（图片/视频/缩略图）"""
    return action_library_service.upload_action_media(db, action_id, file, media_type, UPLOADS_DIR)


@router.delete('/actions/media/{media_id}')
def delete_action_media(
    media_id: int,
    db: Session = Depends(get_db),
    coach: User = Depends(require_role(*COACH_OR_ADMIN)),
):
    """删除动作媒体文件"""
    return action_library_service.delete_action_media(db, media_id)
