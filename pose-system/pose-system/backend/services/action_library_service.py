# -*- coding: utf-8 -*-
"""
Action Library Management Service
动作库管理 — 合并 DB + JSON 数据源，支持教练查看、编辑、新建动作，上传媒体

Extracted from coach_service.py to maintain single-responsibility architecture:
  coach_service → class/student management
  action_library_service → action library CRUD + media
"""
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from backend.database import models
from backend.database.models import User, ActionLibrary, ActionMedia


# ── Lazy-loaded JSON caches ────────────────────────────────────────────

_JSON_ACTION_CACHE = None
_STANDARD_ACTIONS_CACHE = None


def _load_json_actions():
    """Lazy-load action_library.json."""
    global _JSON_ACTION_CACHE
    if _JSON_ACTION_CACHE is None:
        al_path = Path(__file__).resolve().parent.parent.parent / "models" / "prescription_v2" / "action_library.json"
        if al_path.exists():
            with open(al_path, "r", encoding="utf-8") as f:
                _JSON_ACTION_CACHE = json.load(f).get("actions", [])
        else:
            _JSON_ACTION_CACHE = []
    return _JSON_ACTION_CACHE


def _load_standard_actions():
    """Lazy-load standard_actions.json."""
    global _STANDARD_ACTIONS_CACHE
    if _STANDARD_ACTIONS_CACHE is None:
        sa_path = Path(__file__).resolve().parent.parent.parent / "models" / "knowledge" / "standard_actions.json"
        if sa_path.exists():
            with open(sa_path, "r", encoding="utf-8") as f:
                _STANDARD_ACTIONS_CACHE = json.load(f).get("actions", {})
        else:
            _STANDARD_ACTIONS_CACHE = {}
    return _STANDARD_ACTIONS_CACHE


# ── JSON parsing helpers ───────────────────────────────────────────────

def _json_list_parse(v):
    """Parse a JSON string to list, or return as-is if already a list."""
    if v is None:
        return []
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return [v] if v else []
    if isinstance(v, list):
        return v
    return []


def _json_dict_parse(v):
    """Parse a JSON string to dict."""
    if v is None:
        return None
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, TypeError):
            return None
    if isinstance(v, dict):
        return v
    return None


# ── Merge logic ────────────────────────────────────────────────────────

def _merge_action(db_row, jdata: dict, has_standard: bool) -> dict:
    """Merge a DB row and JSON data into a unified action dict.
    DB takes priority for fields that exist in both.
    """
    media_list = []
    if db_row and hasattr(db_row, 'media') and db_row.media:
        media_list = [
            {
                'id': m.id,
                'media_type': m.media_type,
                'file_path': m.file_path,
                'url': f'/media/uploads/actions/{m.file_path}' if not m.file_path.startswith('http') else m.file_path,
                'original_filename': m.original_filename,
                'file_size': m.file_size,
                'sort_order': m.sort_order,
            }
            for m in db_row.media
        ]

    def _pick(db_val, json_val, default=None):
        if db_row and db_val is not None and db_val != '':
            return db_val
        if json_val is not None and json_val != '' and json_val != []:
            return json_val
        return default

    return {
        'source': 'custom' if (db_row and db_row.is_custom) else ('db' if db_row else 'json'),
        'id': db_row.id if db_row else None,
        'json_id': jdata.get('id') if jdata else None,
        'name': _pick(
            db_row.name if db_row else None,
            jdata.get('name') if jdata else None,
            ''
        ),
        'family': _pick(
            db_row.family if db_row else None,
            jdata.get('family') if jdata else None,
        ),
        'family_name': _pick(
            db_row.family_name if db_row else None,
            jdata.get('family_name') if jdata else None,
        ),
        'category': _pick(
            db_row.category if db_row else None,
            jdata.get('category') if jdata else None,
        ),
        'subcategory': _pick(
            None,
            jdata.get('subcategory') if jdata else None,
        ),
        'difficulty': _pick(
            db_row.difficulty if db_row else None,
            jdata.get('difficulty') if jdata else None,
            1,
        ),
        'intensity': _pick(
            None,
            jdata.get('intensity') if jdata else None,
            'MEDIUM',
        ),
        'target_body_parts': _json_list_parse(
            _pick(
                db_row.target_body_parts if db_row else None,
                jdata.get('target_body_parts') if jdata else None,
                [],
            )
        ),
        'phases': _pick(
            None,
            jdata.get('phases') if jdata else None,
            [],
        ),
        'description': _pick(
            db_row.description if db_row else None,
            jdata.get('description') if jdata else None,
        ),
        'steps': _json_list_parse(
            _pick(
                db_row.steps if db_row else None,
                jdata.get('steps') if jdata else None,
                [],
            )
        ),
        'cues': _json_list_parse(
            _pick(
                db_row.cues if db_row else None,
                jdata.get('cues') if jdata else None,
                [],
            )
        ),
        'contraindications': _json_dict_parse(
            _pick(
                db_row.contraindications if db_row else None,
                jdata.get('contraindications') if jdata else None,
            )
        ),
        'video_url': _pick(
            db_row.video_url if db_row else None,
            jdata.get('display_url') if jdata and jdata.get('display_type') == 'video' else None,
        ),
        'thumbnail_url': _pick(
            db_row.thumbnail_url if db_row else None,
            jdata.get('display_url') if jdata and jdata.get('display_type') == 'image' else None,
        ),
        'media': media_list,
        'is_custom': db_row.is_custom if db_row else False,
        'is_visible': db_row.is_visible if db_row else True,
        'has_standard_angles': has_standard,
        'created_at': str(db_row.created_at) if db_row and db_row.created_at else None,
        'updated_at': str(db_row.updated_at) if db_row and hasattr(db_row, 'updated_at') and db_row.updated_at else None,
    }


# ── Public API ─────────────────────────────────────────────────────────

def get_merged_action_library(
    db: Session,
    category: str = None,
    family: str = None,
    difficulty: int = None,
    body_part: str = None,
    search: str = None,
    page: int = 1,
    page_size: int = 20,
    include_hidden: bool = False,
) -> dict:
    """Merge DB + JSON action sources with filtering and pagination.

    Args:
        include_hidden: 为 True 时也返回隐藏动作（教练可查看并取消隐藏）
    """
    json_actions = _load_json_actions()
    standard_actions = _load_standard_actions()
    db_actions = db.query(models.ActionLibrary).all()

    json_by_name = {a["name"]: a for a in json_actions}

    # 收集被隐藏的动作名称（DB 记录 + 影子记录）
    hidden_names = {a.name for a in db_actions if not a.is_visible}

    merged = []
    all_names = set()

    # 1. DB actions
    for a in db_actions:
        if not a.is_visible and not include_hidden:
            continue
        all_names.add(a.name)
        jdata = json_by_name.get(a.name, {})
        has_standard = a.name in standard_actions
        merged.append(_merge_action(a, jdata, has_standard))

    # 2. JSON-only actions — 跳过被影子记录标记为隐藏的（除非 include_hidden）
    for a in json_actions:
        if a["name"] not in all_names and a["name"] not in (hidden_names if not include_hidden else set()):
            all_names.add(a["name"])
            has_standard = a["name"] in standard_actions
            merged.append(_merge_action(None, a, has_standard))

    # 3. Filtering
    if category:
        merged = [a for a in merged if a.get('category') == category or
                  (a.get('category', '') or '').lower() == category.lower()]
    if family:
        merged = [a for a in merged if a.get('family') == family]
    if difficulty is not None:
        merged = [a for a in merged if a.get('difficulty') == difficulty]
    if body_part:
        merged = [
            a for a in merged
            if any(body_part.lower() in bp.lower() for bp in (a.get('target_body_parts') or []))
        ]
    if search:
        sl = search.lower()
        merged = [
            a for a in merged
            if sl in (a.get('name', '') or '').lower()
            or sl in (a.get('family_name', '') or '').lower()
            or sl in (a.get('description', '') or '').lower()
        ]

    # Sort: custom first, then by difficulty, then by name
    merged.sort(key=lambda a: (not a.get('is_custom'), a.get('difficulty', 1), a.get('name', '')))

    total = len(merged)
    start = (page - 1) * page_size
    paged = merged[start:start + page_size]

    families = sorted(set(
        (a.get('family') or '') for a in merged if a.get('family')
    ))
    categories = sorted(set(
        (a.get('category') or '') for a in merged if a.get('category')
    ))

    return {
        'items': paged,
        'total': total,
        'page': page,
        'page_size': page_size,
        'families': families,
        'categories': categories,
    }


def get_action_detail_unified(db: Session, action_id) -> dict:
    """Get a single action's merged detail. Accepts int (DB id) or str (JSON id/name)."""
    json_actions = {a["name"]: a for a in _load_json_actions()}
    standard_actions = _load_standard_actions()

    db_row = None
    jdata = None

    if isinstance(action_id, int) or (isinstance(action_id, str) and action_id.isdigit()):
        db_row = db.query(models.ActionLibrary).filter(
            models.ActionLibrary.id == int(action_id)
        ).first()
        if db_row:
            jdata = json_actions.get(db_row.name, {})
        else:
            raise HTTPException(status_code=404, detail='Action not found')
    else:
        jdata = json_actions.get(action_id)
        if not jdata:
            for a in _load_json_actions():
                if a.get("id") == action_id:
                    jdata = a
                    break
        if jdata:
            db_row = db.query(models.ActionLibrary).filter(
                models.ActionLibrary.name == jdata["name"]
            ).first()
        else:
            db_row = db.query(models.ActionLibrary).filter(
                models.ActionLibrary.name == action_id
            ).first()
            if db_row:
                jdata = json_actions.get(db_row.name, {})

        if not db_row and not jdata:
            raise HTTPException(status_code=404, detail='Action not found')

    has_standard = (db_row.name if db_row else jdata.get("name", "")) in standard_actions
    return _merge_action(db_row, jdata, has_standard)


def update_action_metadata(db: Session, action_id: int, data: dict, coach: User) -> dict:
    """Update action metadata."""
    db_row = db.query(models.ActionLibrary).filter(models.ActionLibrary.id == action_id).first()
    if not db_row:
        raise HTTPException(status_code=404, detail='Action not found')

    allowed = {
        'name', 'category', 'difficulty', 'description',
        'steps', 'cues', 'contraindications', 'family', 'family_name',
        'target_body_parts', 'video_url', 'thumbnail_url',
    }
    for key, value in data.items():
        if key not in allowed:
            continue
        if key in ('steps', 'cues'):
            value = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
        if key == 'contraindications':
            value = json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value
        if key == 'target_body_parts':
            value = json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value
        setattr(db_row, key, value)

    db_row.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_row)
    return _merge_action(db_row, {}, False)


def create_custom_action(db: Session, data: dict, coach: User) -> dict:
    """Create a new custom action."""
    if not data.get('name'):
        raise HTTPException(status_code=400, detail='Action name is required')

    existing = db.query(models.ActionLibrary).filter(
        models.ActionLibrary.name == data['name']
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail='Action with this name already exists')

    action = models.ActionLibrary(
        name=data['name'],
        category=data.get('category', '自定义'),
        difficulty=data.get('difficulty', 1),
        description=data.get('description', ''),
        steps=json.dumps(data.get('steps', []), ensure_ascii=False) if data.get('steps') else None,
        cues=json.dumps(data.get('cues', []), ensure_ascii=False) if data.get('cues') else None,
        target_body_parts=json.dumps(data.get('target_body_parts', []), ensure_ascii=False) if data.get('target_body_parts') else None,
        family=data.get('family'),
        family_name=data.get('family_name'),
        video_url=data.get('video_url'),
        thumbnail_url=data.get('thumbnail_url'),
        is_custom=True,
        created_by=coach.id,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return _merge_action(action, {}, False)


def upload_action_media(
    db: Session, action_id: int, file, media_type: str, upload_dir: str
) -> dict:
    """Save uploaded file and create ActionMedia record."""
    action = db.query(models.ActionLibrary).filter(models.ActionLibrary.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail='Action not found')

    ext = os.path.splitext(file.filename or '')[1].lower()
    allowed_image = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    allowed_video = {'.mp4', '.webm'}
    allowed = allowed_image if media_type in ('image', 'thumbnail') else allowed_video
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f'不支持的文件类型: {ext}')

    max_size = 10 * 1024 * 1024 if media_type in ('image', 'thumbnail') else 100 * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise HTTPException(status_code=400, detail=f'文件大小不能超过 {limit_mb}MB')

    unique_name = f"{action_id}_{media_type}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = os.path.join(upload_dir, unique_name)
    os.makedirs(upload_dir, exist_ok=True)

    with open(save_path, "wb") as f:
        f.write(file.file.read())

    media = models.ActionMedia(
        action_id=action_id,
        media_type=media_type,
        file_path=unique_name,
        original_filename=file.filename,
        file_size=file_size,
    )
    db.add(media)
    db.commit()
    db.refresh(media)

    if media_type in ('thumbnail', 'image') and not action.thumbnail_url:
        action.thumbnail_url = f'/media/uploads/actions/{unique_name}'
    if media_type == 'video' and not action.video_url:
        action.video_url = f'/media/uploads/actions/{unique_name}'
    db.commit()

    return {
        'id': media.id,
        'media_type': media.media_type,
        'file_path': media.file_path,
        'url': f'/media/uploads/actions/{unique_name}',
        'original_filename': media.original_filename,
        'file_size': media.file_size,
    }


def delete_action(db: Session, action_id: int, coach: User) -> dict:
    """软删除自定义动作（仅限 is_custom=True 的动作）。"""
    action = db.query(models.ActionLibrary).filter(
        models.ActionLibrary.id == action_id
    ).first()
    if not action:
        raise HTTPException(status_code=404, detail='动作不存在')
    if not action.is_custom:
        raise HTTPException(status_code=400, detail='系统内置动作不可删除，请使用隐藏功能')
    action.is_visible = False
    action.updated_at = datetime.utcnow()
    db.commit()
    return {'message': '动作已删除', 'action_id': action_id}


def set_action_visibility(db: Session, identifier: str, visible: bool, coach: User) -> dict:
    """设置动作的可见性。identifier 可以是 DB id（数字）或动作名称（字符串）。

    - DB 动作：直接更新 is_visible 字段
    - JSON 动作：创建/更新影子 DB 记录
    """
    # 尝试作为数字 ID 处理
    try:
        action_id = int(identifier)
        action = db.query(models.ActionLibrary).filter(
            models.ActionLibrary.id == action_id
        ).first()
        if action:
            action.is_visible = visible
            action.updated_at = datetime.utcnow()
            db.commit()
            return {'message': '可见性已更新', 'name': action.name, 'is_visible': visible}
    except ValueError:
        pass

    # identifier 是动作名称 — 查找或创建 DB 影子记录
    name = identifier
    action = db.query(models.ActionLibrary).filter(
        models.ActionLibrary.name == name
    ).first()

    if action:
        action.is_visible = visible
        action.updated_at = datetime.utcnow()
    else:
        # 为 JSON 内置动作创建影子记录
        action = models.ActionLibrary(
            name=name,
            is_custom=False,
            is_visible=visible,
        )
        db.add(action)

    db.commit()
    return {'message': '可见性已更新', 'name': name, 'is_visible': visible}


def delete_action_media(db: Session, media_id: int) -> dict:
    """Delete a media record and its physical file."""
    media = db.query(models.ActionMedia).filter(models.ActionMedia.id == media_id).first()
    if not media:
        raise HTTPException(status_code=404, detail='Media not found')

    upload_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "uploads", "actions"
    )
    file_path = os.path.join(upload_dir, media.file_path)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass

    db.delete(media)
    db.commit()
    return {'message': 'Media deleted'}
