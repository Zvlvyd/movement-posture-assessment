# -*- coding: utf-8 -*-
"""
动作库种子数据加载器
将 JSON 知识库中的动作数据加载到数据库 ActionLibrary 表中。
在主应用启动时自动执行，已有数据则跳过。
"""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from backend.database import models

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent.parent / "models" / "knowledge"

def seed_action_library(db: Session):
    """从 standard_actions.json 和 exercises.json 加载动作到 ActionLibrary。"""
    existing_count = db.query(models.ActionLibrary).count()
    if existing_count > 10:
        return  # 已有数据，跳过

    actions_added = 0

    # 1. 从 standard_actions.json 加载标准训练动作（深蹲、弓步蹲等）
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

    # 2. 从 exercises.json 加载体态矫正动作
    ex_path = KNOWLEDGE_DIR / "exercises.json"
    if ex_path.exists():
        with open(ex_path, "r", encoding="utf-8") as f:
            ex_data = json.load(f)
        for problem_id, problem_data in ex_data.items():
            for cat_key in ("stretch", "strength"):
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
                            category=f"体态-{cat_key}",
                            difficulty=diff,
                            target_body_parts=problem_id,
                            description=combined_desc[:500],
                        ))
                        actions_added += 1

    if actions_added > 0:
        db.commit()

    # 3. 加载 ProblemTag 和 TagActionMapping
    prob_path = KNOWLEDGE_DIR / "problems.json"
    if prob_path.exists():
        with open(prob_path, "r", encoding="utf-8") as f:
            prob_data = json.load(f)
        for prob_id, prob_info in prob_data.items():
            tag = db.query(models.ProblemTag).filter(
                models.ProblemTag.name == prob_id
            ).first()
            if not tag:
                db.add(models.ProblemTag(
                    name=prob_id,
                    description=prob_info.get("name", prob_id),
                    severity=2,
                ))
    db.commit()
