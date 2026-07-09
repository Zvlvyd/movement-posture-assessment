# -*- coding: utf-8 -*-
"""
Message service — send, list conversations, mark read, unread count.

Supports lightweight non-real-time communication between coaches and trainees.
"""
from typing import List, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, func
from fastapi import HTTPException

from backend.database.models import User, Message


# ── Send ───────────────────────────────────────────────────────────

def send_message(db: Session, sender: User, receiver_id: int, content: str,
                 related_type: str = None, related_id: int = None) -> dict:
    """Send a message from sender to receiver."""
    receiver = db.query(User).filter(User.id == receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="接收用户不存在")

    msg = Message(
        sender_id=sender.id,
        receiver_id=receiver_id,
        content=content,
        related_type=related_type,
        related_id=related_id,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return {
        'id': msg.id,
        'sender_id': msg.sender_id,
        'receiver_id': msg.receiver_id,
        'content': msg.content,
        'is_read': msg.is_read,
        'created_at': str(msg.created_at),
    }


# ── List Conversations ──────────────────────────────────────────────

def list_conversations(db: Session, user: User, page: int = 1, page_size: int = 20) -> dict:
    """
    Get list of conversation partners for the current user.
    Returns the latest message with each unique conversation partner.
    """
    # Find all unique users the current user has communicated with
    sent_to = db.query(Message.receiver_id).filter(Message.sender_id == user.id).distinct().all()
    received_from = db.query(Message.sender_id).filter(Message.receiver_id == user.id).distinct().all()

    partner_ids = set()
    for r in sent_to + received_from:
        partner_ids.add(r[0])

    conversations = []
    for partner_id in partner_ids:
        partner = db.query(User).filter(User.id == partner_id).first()
        if not partner:
            continue

        # Get latest message
        latest = db.query(Message).filter(
            or_(
                and_(Message.sender_id == user.id, Message.receiver_id == partner_id),
                and_(Message.sender_id == partner_id, Message.receiver_id == user.id),
            )
        ).order_by(desc(Message.created_at)).first()

        # Count unread from this partner
        unread = db.query(func.count(Message.id)).filter(
            Message.sender_id == partner_id,
            Message.receiver_id == user.id,
            Message.is_read == False,
        ).scalar() or 0

        conversations.append({
            'partner_id': partner_id,
            'partner_name': partner.username,
            'partner_role': partner.role.value if hasattr(partner.role, 'value') else str(partner.role),
            'last_message': latest.content[:100] if latest else '',
            'last_time': str(latest.created_at) if latest else '',
            'unread_count': unread,
        })

    # Sort by last_time descending
    conversations.sort(key=lambda c: c['last_time'], reverse=True)

    total = len(conversations)
    start = (page - 1) * page_size
    return {
        'conversations': conversations[start:start + page_size],
        'total': total,
    }


# ── Conversation with User ─────────────────────────────────────────

def get_messages_with(db: Session, user: User, partner_id: int,
                      page: int = 1, page_size: int = 50) -> dict:
    """Get all messages between current user and another user."""
    partner = db.query(User).filter(User.id == partner_id).first()
    if not partner:
        raise HTTPException(status_code=404, detail="用户不存在")

    messages = db.query(Message).filter(
        or_(
            and_(Message.sender_id == user.id, Message.receiver_id == partner_id),
            and_(Message.sender_id == partner_id, Message.receiver_id == user.id),
        )
    ).order_by(desc(Message.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    # Mark incoming messages as read
    for m in messages:
        if m.receiver_id == user.id and not m.is_read:
            m.is_read = True
    db.commit()

    return {
        'partner': {
            'id': partner.id,
            'username': partner.username,
            'role': partner.role.value if hasattr(partner.role, 'value') else str(partner.role),
        },
        'messages': [
            {
                'id': m.id,
                'sender_id': m.sender_id,
                'receiver_id': m.receiver_id,
                'content': m.content,
                'is_read': m.is_read,
                'related_type': m.related_type,
                'related_id': m.related_id,
                'created_at': str(m.created_at),
            }
            for m in reversed(messages)  # Return in chronological order
        ],
        'total': len(messages),
    }


# ── Unread Count ───────────────────────────────────────────────────

def get_unread_count(db: Session, user: User) -> dict:
    """Get total unread message count for the current user."""
    count = db.query(func.count(Message.id)).filter(
        Message.receiver_id == user.id,
        Message.is_read == False,
    ).scalar() or 0

    return {'unread_count': count}


# ── Mark Read ──────────────────────────────────────────────────────

def mark_read(db: Session, user: User, message_id: int) -> dict:
    """Mark a specific message as read."""
    msg = db.query(Message).filter(
        Message.id == message_id,
        Message.receiver_id == user.id,
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="消息不存在")

    msg.is_read = True
    db.commit()
    return {'message': '已标记为已读'}
