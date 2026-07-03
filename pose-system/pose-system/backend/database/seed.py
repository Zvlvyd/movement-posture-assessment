# -*- coding: utf-8 -*-
"""
动作库种子数据加载器
将 JSON 知识库中的动作数据加载到数据库 ActionLibrary 表中。
在主应用启动时自动执行，已有数据则跳过。
"""
import json
import os
from pathlib import Path
from datetime import datetime
from backend.logger import get_logger

logger = get_logger(__name__)
from sqlalchemy.orm import Session
from backend.database import models

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "knowledge"
PRESCRIPTION_V2_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "prescription_v2"


def _json_list(value):
    """将 Python 列表转为 JSON 字符串存储。"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def seed_action_library(db: Session):
    """从多个 JSON 源加载动作数据到 ActionLibrary，并补充新字段。"""
    actions_added = 0
    actions_updated = 0

    # 1. 从 action_library.json 加载丰富的动作元数据
    al_path = PRESCRIPTION_V2_DIR / "action_library.json"
    json_actions = {}
    if al_path.exists():
        with open(al_path, "r", encoding="utf-8") as f:
            al_data = json.load(f)
        for action in al_data.get("actions", []):
            json_actions[action["name"]] = action

    # 2. 遍历所有现有 DB 记录，补充缺失字段
    existing_actions = db.query(models.ActionLibrary).all()
    for row in existing_actions:
        jdata = json_actions.get(row.name)
        if jdata:
            updated = False
            if not row.family:
                row.family = jdata.get("family")
                updated = True
            if not row.family_name:
                row.family_name = jdata.get("family_name")
                updated = True
            if not row.steps:
                row.steps = _json_list(jdata.get("steps"))
                updated = True
            if not row.cues:
                row.cues = _json_list(jdata.get("cues"))
                updated = True
            if not row.contraindications:
                row.contraindications = _json_list(jdata.get("contraindications"))
                updated = True
            if updated:
                actions_updated += 1

    # 3. 将 JSON 中存在但 DB 中不存在的动作插入 DB
    for name, jdata in json_actions.items():
        existing = db.query(models.ActionLibrary).filter(
            models.ActionLibrary.name == name
        ).first()
        if not existing:
            db.add(models.ActionLibrary(
                name=name,
                category=jdata.get("category", "general"),
                difficulty=jdata.get("difficulty", 2),
                target_body_parts=_json_list(jdata.get("target_body_parts")),
                description=jdata.get("description", ""),
                steps=_json_list(jdata.get("steps")),
                cues=_json_list(jdata.get("cues")),
                contraindications=_json_list(jdata.get("contraindications")),
                family=jdata.get("family"),
                family_name=jdata.get("family_name"),
                video_url=jdata.get("display_url") if jdata.get("display_type") == "video" else None,
                thumbnail_url=jdata.get("display_url") if jdata.get("display_type") == "image" else None,
                is_custom=False,
            ))
            actions_added += 1

    # 4. 从 standard_actions.json 补充标准角度动作（仅新增 DB 中不存在的）
    sa_path = KNOWLEDGE_DIR / "standard_actions.json"
    if sa_path.exists():
        with open(sa_path, "r", encoding="utf-8") as f:
            sa_data = json.load(f)
        for action_name, action_data in sa_data.get("actions", {}).items():
            existing = db.query(models.ActionLibrary).filter(
                models.ActionLibrary.name == action_name
            ).first()
            if not existing:
                cat = action_data.get("category", "general")
                desc = action_data.get("description", "")
                db.add(models.ActionLibrary(
                    name=action_name,
                    category=cat,
                    difficulty=2,
                    target_body_parts=cat,
                    description=desc,
                ))
                actions_added += 1

    # 5. 从 exercises.json 加载体态矫正动作
    ex_path = KNOWLEDGE_DIR / "exercises.json"
    if ex_path.exists():
        with open(ex_path, "r", encoding="utf-8") as f:
            ex_data = json.load(f)
        for problem_id, problem_data in ex_data.items():
            for cat_key in ("stretch", "strength"):
                # 统一分类：拉伸 → "拉伸"，力量 → "体态矫正"
                category = "拉伸" if cat_key == "stretch" else "体态矫正"
                for ex in problem_data.get(cat_key, []):
                    name = ex.get("name", "")
                    if not name:
                        continue
                    existing = db.query(models.ActionLibrary).filter(
                        models.ActionLibrary.name == name
                    ).first()
                    if not existing:
                        combined_desc = " ".join(ex.get("steps", []))
                        diff = 1 if cat_key == "stretch" else 2
                        db.add(models.ActionLibrary(
                            name=name,
                            category=category,
                            difficulty=diff,
                            target_body_parts=problem_id,
                            description=combined_desc[:500],
                        ))
                        actions_added += 1

    if actions_added > 0 or actions_updated > 0:
        db.commit()
        logger.info("[seed] ActionLibrary: added %d, updated %d", actions_added, actions_updated)

    # 6. 加载 ProblemTag（使用中文显示名）和 TagActionMapping
    prob_path = KNOWLEDGE_DIR / "problems.json"
    if prob_path.exists():
        with open(prob_path, "r", encoding="utf-8") as f:
            prob_data = json.load(f)

        # 建立英文key → 中文名映射
        en_to_cn = {}
        for prob_id, prob_info in prob_data.items():
            en_to_cn[prob_id] = prob_info.get("name", prob_id)

        for prob_id, prob_info in prob_data.items():
            cn_name = prob_info.get("name", prob_id)
            # 优先按中文名查找，兼容旧数据按英文key查找
            tag = db.query(models.ProblemTag).filter(
                models.ProblemTag.name == cn_name
            ).first()
            if not tag:
                # 兼容旧数据：检查是否存在英文key命名的记录
                old_tag = db.query(models.ProblemTag).filter(
                    models.ProblemTag.name == prob_id
                ).first()
                if old_tag:
                    # 迁移旧记录：将英文名更新为中文名
                    old_tag.name = cn_name
                    old_tag.description = f"[{prob_id}] {prob_info.get('cause', '')}"
                    logger.info("[seed] ProblemTag migrated: %s → %s", prob_id, cn_name)
                else:
                    db.add(models.ProblemTag(
                        name=cn_name,
                        description=f"[{prob_id}] {prob_info.get('cause', '')}",
                        severity=2,
                    ))

        db.commit()
        logger.info("[seed] ProblemTag: %d tags seeded/migrated", len(prob_data))

        # 7. 加载 TagActionMapping（动作→体态问题映射，来自 action_library.json）
        al_path = PRESCRIPTION_V2_DIR / "action_library.json"
        if al_path.exists():
            with open(al_path, "r", encoding="utf-8") as f:
                al_data = json.load(f)

            mapping_added = 0
            for action in al_data.get("actions", []):
                problem_mapping = action.get("problem_mapping", {})
                if not problem_mapping:
                    continue

                # 查找DB中的动作记录
                db_action = db.query(models.ActionLibrary).filter(
                    models.ActionLibrary.name == action["name"]
                ).first()
                if not db_action:
                    continue

                for prob_id, relevance in problem_mapping.items():
                    if relevance <= 0:
                        continue
                    # 用中文名查找 ProblemTag
                    cn_name = en_to_cn.get(prob_id, prob_id)
                    tag = db.query(models.ProblemTag).filter(
                        models.ProblemTag.name == cn_name
                    ).first()
                    if not tag:
                        continue

                    # 检查映射是否已存在
                    existing_map = db.query(models.TagActionMapping).filter(
                        models.TagActionMapping.tag_id == tag.id,
                        models.TagActionMapping.action_id == db_action.id,
                    ).first()
                    if not existing_map:
                        db.add(models.TagActionMapping(
                            tag_id=tag.id,
                            action_id=db_action.id,
                            relevance_score=relevance,
                        ))
                        mapping_added += 1

            if mapping_added > 0:
                db.commit()
                logger.info("[seed] TagActionMapping: added %d mappings", mapping_added)


def seed_system_config(db: Session):
    """初始化系统配置默认值（不存在则创建）。"""
    defaults = [
        ("model_path", "yolov8s-pose.pt", "YOLO 姿态估计模型路径"),
        ("high_precision_model_path", "", "高精度模型路径（可选）"),
        ("device", "auto", "运行设备 (auto/cpu/cuda:0)"),
        ("rate_limit_auth_per_minute", "5", "认证接口每分钟限流次数"),
        ("assessment_confidence_threshold", "0.5", "评估置信度阈值"),
    ]
    for key, value, desc in defaults:
        existing = db.query(models.SystemConfig).filter(
            models.SystemConfig.config_key == key
        ).first()
        if not existing:
            db.add(models.SystemConfig(
                config_key=key,
                config_value=value,
                description=desc,
            ))
    db.commit()
    logger.info("[seed] SystemConfig: defaults initialized")


def seed_users(db: Session):
    """创建默认管理员和教练账号（如不存在则创建）。

    账号凭据从 config.settings 读取，支持环境变量覆盖。
    已在数据库中存在同名用户时跳过，保证幂等。
    如果密码未设置，自动生成随机安全密码并打印到控制台。
    """
    import secrets
    from shared.security import hash_password
    from config.settings import settings

    defaults = [
        (settings.DEFAULT_ADMIN_USERNAME, settings.DEFAULT_ADMIN_PASSWORD, models.UserRole.ADMIN),
        (settings.DEFAULT_COACH_USERNAME, settings.DEFAULT_COACH_PASSWORD, models.UserRole.COACH),
    ]

    for username, password, role in defaults:
        existing = db.query(models.User).filter(
            models.User.username == username
        ).first()
        if existing:
            continue
        if not password:
            password = secrets.token_urlsafe(16)
            logger.warning(
                "[seed] %s 密码未设置，已自动生成随机密码: %s  (请妥善保存，重启不会再次打印)",
                role.value, password,
            )
        user = models.User(
            username=username,
            password_hash=hash_password(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        logger.info("[seed] Created %s account: username=%s", role.value, username)

    db.commit()
