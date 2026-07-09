# -*- coding: utf-8 -*-
"""Message router — send, list conversations, get messages with user, mark read."""
from fastapi import APIRouter, Depends, Query
from backend.database.connection import get_db
from backend.services.auth_service import get_current_user
from backend.database.models import User
from backend.services import message_service

router = APIRouter(prefix="/api/messages", tags=["Messages"])


@router.get("", summary="获取会话列表")
def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """获取当前用户的所有会话伙伴及最新消息"""
    return message_service.list_conversations(db, user, page, page_size)


@router.get("/unread-count", summary="获取未读消息数")
def unread_count(
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    return message_service.get_unread_count(db, user)


@router.get("/with/{partner_id}", summary="获取与某用户的对话")
def get_messages_with(
    partner_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """获取当前用户与指定用户的所有消息（自动标记已读）"""
    return message_service.get_messages_with(db, user, partner_id, page, page_size)


@router.post("", summary="发送消息")
def send_message(
    receiver_id: int,
    content: str,
    related_type: str = None,
    related_id: int = None,
    sender: User = Depends(get_current_user),
    db=Depends(get_db),
):
    """发送一条消息"""
    return message_service.send_message(db, sender, receiver_id, content, related_type, related_id)


@router.put("/{message_id}/read", summary="标记消息为已读")
def mark_read(
    message_id: int,
    user: User = Depends(get_current_user),
    db=Depends(get_db),
):
    return message_service.mark_read(db, user, message_id)
