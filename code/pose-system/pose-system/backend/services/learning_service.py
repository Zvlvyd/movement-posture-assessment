# -*- coding: utf-8 -*-
"""
标准学习服务 - 实时姿态对比与精细反馈
处理 WebSocket 连接，实现用户动作与标准动作的逐帧对比

模块结构:
  UnifiedActionLoader — 单例，合并 action_library.json + standard_actions.json
  LearningService      — REST 查询服务
  RealtimeLearningService — WebSocket 逐帧对比（含自动完成、人体检测）
"""
import json
import math
import time
import os
from pathlib import Path
from backend.logger import get_logger

logger = get_logger(__name__)
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from fastapi import WebSocket
from sqlalchemy.orm import Session

from models.angle_calculator import AngleCalculator
from backend.database import models
from backend.services.base import BaseWebSocketHandler


KNOWLEDGE_DIR = Path(__file__).parent.parent.parent / "models" / "knowledge"
PRESCRIPTION_V2_DIR = Path(__file__).parent.parent.parent / "models" / "prescription_v2"

# ── 自动完成 / 人体检测 常量 ──────────────────────────
AUTO_COMPLETE_STREAK = 30          # 连续高分帧数触发自动完成
AUTO_COMPLETE_THRESHOLD = 85       # 被视为"高分"的最低分数
MIN_KEYPOINTS_FOR_BODY = 10        # 确认人体在画面中的最少关键点数（置信度 ≥ 0.15）
YOLO_CONF_THRESHOLD = 0.15         # YOLO 人员检测置信度（低于 Ultralytics 默认 0.25，提高部分遮挡检测率）


class UnifiedActionLoader:
    """统一动作加载器 — 合并 action_library.json (58动作) 和 standard_actions.json (含标准角度)"""

    _instance = None
    _actions_list = None        # list from action_library.json
    _actions_by_name = None     # dict by name
    _actions_by_id = None       # dict by action id
    _standard_data = None       # dict from standard_actions.json
    _families = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._actions_list is not None:
            return

        # Load action_library.json (55 actions, 10 families)
        lib_path = PRESCRIPTION_V2_DIR / "action_library.json"
        with open(lib_path, "r", encoding="utf-8") as f:
            lib_data = json.load(f)
        self._actions_list = lib_data.get("actions", [])
        self._actions_by_name = {}
        self._actions_by_id = {}
        self._families = set()
        for a in self._actions_list:
            self._actions_by_name[a["name"]] = a
            self._actions_by_id[a["id"]] = a
            self._families.add(a.get("family", ""))

        # Load standard_actions.json (standard angles for some actions)
        std_path = KNOWLEDGE_DIR / "standard_actions.json"
        with open(std_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._standard_data = raw.get("actions", {})

        # 向后兼容别名映射（旧名称 → 新名称）
        # v2.0 统一命名：标准动作名前加"标准"前缀，与 action_library.json 对齐
        self._name_aliases = {
            "深蹲": "标准深蹲",
            "俯卧撑": "标准俯卧撑",
            "平板支撑": "标准平板支撑",
        }

    # ---- accessors ----

    @property
    def actions(self) -> List[Dict]:
        return self._actions_list

    def get_by_name(self, name: str) -> Optional[Dict]:
        result = self._actions_by_name.get(name)
        if result:
            return result
        # 向后兼容：尝试别名（旧名称→新名称）
        alias = self._name_aliases.get(name)
        if alias:
            result = self._actions_by_name.get(alias)
            if result:
                return result
        # Fallback: 从 standard_actions.json 构建最小动作字典
        # （处理仅存在于 standard_actions.json 的动作，如"肩部推举"）
        sd = self.get_standard_data(name)
        if sd:
            return {
                "name": name, "id": "", "family": sd.get("family", ""),
                "family_name": sd.get("family_name", ""),
                "category": sd.get("category", ""), "subcategory": "",
                "difficulty": 2, "intensity": "MEDIUM",
                "phases": [], "target_body_parts": [],
                "description": sd.get("description", ""),
                "steps": sd.get("steps", []), "cues": sd.get("cues", []),
            }
        return None

    def get_by_id(self, action_id: str) -> Optional[Dict]:
        return self._actions_by_id.get(action_id)

    def get_standard_data(self, name: str) -> Optional[Dict]:
        """获取该动作在 standard_actions.json 中的标准角度数据（如有）
        支持向后兼容的旧名称别名（如"深蹲"→"标准深蹲"）
        """
        sd = self._standard_data.get(name)
        if sd:
            return sd
        # 向后兼容：尝试别名解析
        alias = self._name_aliases.get(name)
        if alias:
            return self._standard_data.get(alias)
        return None

    def has_standard_angles(self, name: str) -> bool:
        """该动作是否有标准角度数据可用"""
        sd = self.get_standard_data(name)
        if not sd:
            return False
        return bool(sd.get("standard_keypoints"))

    def get_views(self, name: str) -> List[str]:
        """获取支持视角：优先标准数据，否则默认正面"""
        sd = self.get_standard_data(name)
        if sd and sd.get("views"):
            return sd["views"]
        return ["正面"]

    def get_families(self) -> List[str]:
        return sorted(self._families)

    def get_actions_by_family(self, family: str) -> List[Dict]:
        return [a for a in self._actions_list if a.get("family") == family]

    # ── 合并数据源 ──────────────────────────────────────

    def get_merged_action(self, name: str) -> Optional[Dict]:
        """合并 action_library 元信息 + standard_actions 标准角度/视频/错误
        支持向后兼容别名（如"深蹲"→"标准深蹲"）
        """
        lib_action = self._actions_by_name.get(name)
        # 向后兼容：尝试别名
        if not lib_action:
            alias = self._name_aliases.get(name)
            if alias:
                lib_action = self._actions_by_name.get(alias)
                if lib_action:
                    name = alias  # 使用新名称继续查找标准数据
        sd = self._standard_data.get(name, {})
        # 别名查找标准数据
        if not sd:
            alias = self._name_aliases.get(name)
            if alias:
                sd = self._standard_data.get(alias, {})

        if lib_action:
            merged = dict(lib_action)
            merged["standard_keypoints"] = sd.get("standard_keypoints", {})
            merged["common_errors"] = sd.get("common_errors", [])
            merged["video_url"] = sd.get("video_url", "")
            merged["thumbnail_url"] = sd.get("thumbnail_url", "")
            if sd.get("views"):
                merged["views"] = sd["views"]
            elif "views" not in merged:
                merged["views"] = ["正面"]
            return merged

        # 动作仅存在于 standard_actions.json（如"肩部推举"）
        if sd:
            return {
                "name": name, "id": sd.get("id", ""),
                "family": sd.get("family", ""), "family_name": sd.get("family_name", ""),
                "category": sd.get("category", ""), "subcategory": sd.get("subcategory", ""),
                "difficulty": sd.get("difficulty", 2), "intensity": sd.get("intensity", "MEDIUM"),
                "phases": sd.get("phases", []), "target_body_parts": sd.get("target_body_parts", []),
                "description": sd.get("description", ""),
                "steps": sd.get("steps", []), "cues": sd.get("cues", []),
                "views": sd.get("views", ["正面"]),
                "standard_keypoints": sd.get("standard_keypoints", {}),
                "common_errors": sd.get("common_errors", []),
                "video_url": sd.get("video_url", ""),
                "thumbnail_url": sd.get("thumbnail_url", ""),
                "contraindications": sd.get("contraindications", {}),
            }

        return None


class LearningService:
    """标准学习 REST 服务 — 提供统一动作数据查询
    合并三源数据：action_library.json + standard_actions.json + DB ActionLibrary
    DB 中教练上传的媒体（thumbnail_url/video_url）和编辑的元数据优先
    """

    def __init__(self, db: Session = None):
        self.loader = UnifiedActionLoader()
        self._db = db

    def _get_db_override(self, name: str) -> Optional[Dict]:
        """从数据库 ActionLibrary 表查询该动作的覆盖数据（如有）"""
        if self._db is None:
            return None
        row = self._db.query(models.ActionLibrary).filter(
            models.ActionLibrary.name == name
        ).first()
        if not row:
            return None
        # 查询关联媒体列表
        media_list = []
        if hasattr(row, 'media') and row.media:
            media_list = [
                {
                    'id': m.id, 'media_type': m.media_type,
                    'file_path': m.file_path,
                    'url': f'/media/uploads/actions/{m.file_path}',
                    'original_filename': m.original_filename,
                }
                for m in row.media
            ]
        return {
            'description': row.description or None,
            'steps': row.steps or None,
            'cues': row.cues or None,
            'video_url': row.video_url or None,
            'thumbnail_url': row.thumbnail_url or None,
            'category': row.category or None,
            'difficulty': row.difficulty,
            'target_body_parts': row.target_body_parts or None,
            'family': row.family or None,
            'family_name': row.family_name or None,
            'media': media_list,
        }

    @staticmethod
    def _pick(db_val, json_val, default=None):
        """DB 优先于 JSON"""
        if db_val is not None and db_val != '' and db_val != '[]':
            return db_val
        if json_val is not None and json_val != '' and json_val != []:
            return json_val
        return default

    @staticmethod
    def _parse_list(v):
        """将 JSON 字符串解析为列表，或原样返回列表"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return [v] if v else []
        return []

    def list_learnable_actions(self) -> List[Dict]:
        """列出全部可学习的动作（JSON + DB 合并去重）"""
        result = []
        seen_names = set()

        for a in self.loader.actions:
            name = a["name"]
            seen_names.add(name)
            sd = self.loader.get_standard_data(name)
            db = self._get_db_override(name) or {}
            has_angles = self.loader.has_standard_angles(name)
            result.append({
                "name": name, "action_id": a.get("id", ""),
                "family": self._pick(db.get('family'), a.get("family", "")),
                "family_name": self._pick(db.get('family_name'), a.get("family_name", "")),
                "category": self._pick(db.get('category'), a.get("category", "")),
                "subcategory": a.get("subcategory", ""),
                "difficulty": self._pick(db.get('difficulty'), a.get("difficulty", 1)),
                "intensity": a.get("intensity", "MEDIUM"),
                "phases": a.get("phases", []),
                "target_body_parts": self._parse_list(
                    self._pick(db.get('target_body_parts'), a.get("target_body_parts", []))
                ),
                "description": self._pick(db.get('description'), a.get("description", "")),
                "steps": self._parse_list(self._pick(db.get('steps'), a.get("steps", []))),
                "cues": self._parse_list(self._pick(db.get('cues'), a.get("cues", []))),
                "views": self.loader.get_views(name),
                "has_standard_angles": has_angles,
                "common_errors": sd.get("common_errors", []) if sd else [],
                "video_url": self._pick(db.get('video_url'), sd.get("video_url", "") if sd else ""),
                "thumbnail_url": self._pick(db.get('thumbnail_url'), sd.get("thumbnail_url", "") if sd else ""),
                "media": db.get('media', []),
            })

        # standard_actions.json 中未被覆盖的动作
        for name, sd in self.loader._standard_data.items():
            if name in seen_names:
                continue
            db = self._get_db_override(name) or {}
            has_angles = self.loader.has_standard_angles(name)
            result.append({
                "name": name, "action_id": sd.get("id", ""),
                "family": self._pick(db.get('family'), sd.get("family", "")),
                "family_name": self._pick(db.get('family_name'), sd.get("family_name", "")),
                "category": self._pick(db.get('category'), sd.get("category", "")),
                "subcategory": sd.get("subcategory", ""),
                "difficulty": self._pick(db.get('difficulty'), sd.get("difficulty", 2)),
                "intensity": sd.get("intensity", "MEDIUM"),
                "phases": sd.get("phases", []),
                "target_body_parts": self._parse_list(
                    self._pick(db.get('target_body_parts'), sd.get("target_body_parts", []))
                ),
                "description": self._pick(db.get('description'), sd.get("description", "")),
                "steps": self._parse_list(self._pick(db.get('steps'), sd.get("steps", []))),
                "cues": self._parse_list(self._pick(db.get('cues'), sd.get("cues", []))),
                "views": sd.get("views", ["正面"]),
                "has_standard_angles": has_angles,
                "common_errors": sd.get("common_errors", []),
                "video_url": self._pick(db.get('video_url'), sd.get("video_url", "")),
                "thumbnail_url": self._pick(db.get('thumbnail_url'), sd.get("thumbnail_url", "")),
                "media": db.get('media', []),
            })

        return result

    def get_action_detail(self, name: str) -> Optional[Dict]:
        """获取动作详情（合并 JSON + DB，含标准角度）"""
        merged = self.loader.get_merged_action(name)
        if not merged:
            return None
        db = self._get_db_override(name) or {}
        return {
            "name": name, "action_id": merged.get("id", ""),
            "family": self._pick(db.get('family'), merged.get("family", "")),
            "family_name": self._pick(db.get('family_name'), merged.get("family_name", "")),
            "category": self._pick(db.get('category'), merged.get("category", "")),
            "subcategory": merged.get("subcategory", ""),
            "difficulty": self._pick(db.get('difficulty'), merged.get("difficulty", 1)),
            "intensity": merged.get("intensity", "MEDIUM"),
            "phases": merged.get("phases", []),
            "target_body_parts": self._parse_list(
                self._pick(db.get('target_body_parts'), merged.get("target_body_parts", []))
            ),
            "description": self._pick(db.get('description'), merged.get("description", "")),
            "steps": self._parse_list(self._pick(db.get('steps'), merged.get("steps", []))),
            "cues": self._parse_list(self._pick(db.get('cues'), merged.get("cues", []))),
            "views": merged.get("views", ["正面"]),
            "has_standard_angles": self.loader.has_standard_angles(name),
            "standard_keypoints": merged.get("standard_keypoints", {}),
            "common_errors": merged.get("common_errors", []),
            "contraindications": merged.get("contraindications", {}),
            "video_url": self._pick(db.get('video_url'), merged.get("video_url", "")),
            "thumbnail_url": self._pick(db.get('thumbnail_url'), merged.get("thumbnail_url", "")),
            "media": db.get('media', []),
        }

    def get_standard_angles(self, action_name: str, view: str) -> Dict[str, Any]:
        """获取指定动作在指定视角下的标准角度"""
        sd = self.loader.get_standard_data(action_name)
        if not sd:
            return {}
        view_data = sd.get("standard_keypoints", {}).get(view, {})
        return view_data.get("target_angles", {})


class RealtimeLearningService(BaseWebSocketHandler):
    """实时学习 WebSocket 服务 — 逐帧对比、自动完成、人体检测"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.loader = UnifiedActionLoader()

    # ── DB 持久化辅助 ──────────────────────────────────

    def _save_learning_record(
        self, user_id: int, current_action: Optional[Dict],
        current_view: str, avg_score: float, best_score: float,
        frame_count: int, angle_history: List[Dict],
        feedback_counts: Dict[str, int], summary: List[str],
        duration: float,
    ) -> Optional[int]:
        """保存学习记录到 AssessmentRecord 表，返回 record_id"""
        try:
            record = models.AssessmentRecord(
                user_id=user_id,
                balance_score=0, flexibility_score=0,
                upper_limb_score=0, core_score=0, symmetry_score=0,
                overall_score=avg_score,
                risk_level="low" if avg_score >= 70 else ("medium" if avg_score >= 40 else "high"),
                posture_data=json.dumps({
                    "action": current_action.get("name") if current_action else "",
                    "view": current_view,
                }, ensure_ascii=False),
                movement_data=json.dumps({
                    "angle_history": angle_history[-50:],
                }, ensure_ascii=False),
                rom_data=json.dumps({
                    "best_score": best_score, "frame_count": frame_count,
                }, ensure_ascii=False),
                muscle_findings=json.dumps({
                    "feedback_counts": feedback_counts,
                }, ensure_ascii=False),
                report_data=json.dumps({
                    "summary": summary, "duration": duration,
                    "average_score": avg_score, "best_score": best_score,
                }, ensure_ascii=False),
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            return record.id
        except Exception as e:
            logger.warning("[Learning] DB save error: %s", e)
            try:
                self.db.rollback()
            except Exception:
                pass
            return None

    # ── WebSocket 会话主循环 ───────────────────────────

    async def handle_session(self, ws: WebSocket, user_id: int):
        """
        处理标准学习 WebSocket 会话

        客户端 → 服务端:
          {type: "start", action, view}  |  {type: "frame", data: "<base64>"}
          {type: "switch_view", view}    |  {type: "finish"}

        服务端 → 客户端:
          {type: "session_ready", action, standard_angles, key_checks, instruction}
          {type: "comparison", frame, user_angles, user_keypoints, diffs, feedbacks,
                               overall_score, best_score, session_phase}
          {type: "view_switched", view, standard_angles, key_checks}
          {type: "learning_complete", record_id, total_score, summary, auto_triggered, ...}
          {type: "body_confirmed", message, session_phase}
          {type: "error", message}
        """
        current_action = None
        current_view = "正面"
        standard_angles = {}
        common_errors = []
        session_start = None
        frame_count = 0
        angle_history: List[Dict] = []
        total_score_sum = 0.0
        best_score = 0.0
        feedback_counts: Dict[str, int] = {}
        # 自动完成 / 人体检测 状态
        good_streak = 0
        session_phase = "waiting_for_body"   # waiting_for_body | body_confirmed | learning

        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                # ── start ──────────────────────────────
                if msg_type == "start":
                    action_name = msg.get("action", "")
                    current_view = msg.get("view", "正面")

                    if not action_name:
                        await ws.send_json({"type": "error", "message": "请指定学习动作"})
                        continue

                    # 使用 get_merged_action 合并两个数据源
                    merged = self.loader.get_merged_action(action_name)
                    if not merged:
                        await ws.send_json({"type": "error", "message": f"未找到动作: {action_name}"})
                        continue

                    current_action = merged
                    view_data = merged.get("standard_keypoints", {}).get(current_view, {})
                    standard_angles = view_data.get("target_angles", {})
                    common_errors = merged.get("common_errors", [])

                    if not standard_angles:
                        await ws.send_json({
                            "type": "error",
                            "message": f"当前动作「{action_name}」暂未配置标准角度数据，无法进行实时对比学习",
                        })
                        current_action = None
                        continue

                    # 重置 session 状态
                    session_start = time.time()
                    frame_count = 0
                    angle_history = []
                    total_score_sum = 0.0
                    best_score = 0.0
                    feedback_counts = {}
                    good_streak = 0
                    session_phase = "waiting_for_body"

                    await ws.send_json({
                        "type": "session_ready",
                        "action": {
                            "name": action_name,
                            "category": merged.get("category", ""),
                            "description": merged.get("description", ""),
                            "video_url": merged.get("video_url", ""),
                            "views": merged.get("views", ["正面"]),
                        },
                        "current_view": current_view,
                        "standard_angles": standard_angles,
                        "key_checks": view_data.get("key_checks", []),
                        "instruction": f"请面对摄像头，跟随标准示范完成「{action_name}」动作",
                    })

                # ── frame ──────────────────────────────
                elif msg_type == "frame":
                    if current_action is None:
                        await ws.send_json({"type": "error", "message": "请先发送 start 消息"})
                        continue

                    kp_xy, kp_confs, frame = self.extract_keypoints_from_msg(msg, conf=YOLO_CONF_THRESHOLD)
                    # 帧尺寸（YOLO 推理时的实际尺寸，用于前端坐标缩放）
                    fh, fw = frame.shape[:2] if frame is not None else (480, 640)

                    # 完全未检测到人体 — YOLO 未找到任何人
                    if kp_xy is None:
                        good_streak = 0
                        session_phase = "waiting_for_body"
                        await ws.send_json({
                            "type": "comparison",
                            "frame": frame_count,
                            "user_angles": {},
                            "user_keypoints": None,
                            "user_confidences": None,
                            "frame_width": fw,
                            "frame_height": fh,
                            "standard_angles": standard_angles,
                            "diffs": [],
                            "feedbacks": [{"name": "等待人体检测", "severity": "info",
                                           "message": "请让全身进入摄像头范围"}],
                            "overall_score": None,
                            "best_score": best_score,
                            "session_phase": session_phase,
                        })
                        continue

                    # 构建 (17, 3) 关键点数组
                    full_kps = np.zeros((17, 3), dtype=np.float32)
                    full_kps[:, :2] = kp_xy
                    full_kps[:, 2] = kp_confs if kp_confs is not None else np.ones(17)

                    valid_kp_count = int(np.sum(full_kps[:, 2] >= 0.15))
                    kp_list = kp_xy.tolist() if hasattr(kp_xy, "tolist") else kp_xy
                    conf_list = kp_confs if kp_confs is not None else [1.0] * len(kp_list)

                    # 极低关键点 → 仍发送骨架但跳过角度计算
                    if valid_kp_count < MIN_KEYPOINTS_FOR_BODY:
                        good_streak = 0
                        session_phase = "waiting_for_body"
                        await ws.send_json({
                            "type": "comparison",
                            "frame": frame_count,
                            "user_angles": {},
                            "user_keypoints": kp_list,
                            "user_confidences": conf_list,
                            "frame_width": fw,
                            "frame_height": fh,
                            "standard_angles": standard_angles,
                            "diffs": [],
                            "feedbacks": [{"name": "等待完整人体", "severity": "info",
                                           "message": f"已检测到 {valid_kp_count}/17 个关键点，请全身进入摄像头范围"}],
                            "overall_score": None,
                            "best_score": best_score,
                            "session_phase": "waiting_for_body",
                        })
                        frame_count += 1
                        continue

                    # 人体确认 → 进入学习阶段（关键点 ≥ MIN_KEYPOINTS_FOR_BODY = 10）
                    if session_phase == "waiting_for_body":
                        session_phase = "body_confirmed"
                        await ws.send_json({
                            "type": "body_confirmed",
                            "message": "已确认人体，开始实时分析",
                            "session_phase": session_phase,
                        })
                    elif session_phase == "body_confirmed":
                        session_phase = "learning"

                    # 计算用户角度
                    user_angles = self.compute_angles(full_kps)

                    # 与标准角度对比
                    comparison = self._compare_angles(
                        user_angles, standard_angles, common_errors, current_view
                    )

                    frame_count += 1
                    score = comparison.get("overall_score")

                    if score is not None:
                        total_score_sum += score
                        if score > best_score:
                            best_score = score

                    # 自动完成：跟踪连续高分帧
                    if score is not None and score >= AUTO_COMPLETE_THRESHOLD:
                        good_streak += 1
                    else:
                        good_streak = 0

                    angle_history.append({
                        "frame": frame_count,
                        "angles": {k: round(v, 1) for k, v in user_angles.items() if v is not None},
                        "score": score,
                    })

                    for fb in comparison.get("feedbacks", []):
                        name = fb.get("name", "")
                        feedback_counts[name] = feedback_counts.get(name, 0) + 1

                    # 发送逐帧对比结果（含关键点 + 置信度 + 帧尺寸用于前端骨架叠加缩放）
                    await ws.send_json({
                        "type": "comparison",
                        "frame": frame_count,
                        "user_angles": {k: round(v, 1) for k, v in user_angles.items() if v is not None},
                        "user_keypoints": kp_list,
                        "user_confidences": conf_list,
                        "frame_width": fw,
                        "frame_height": fh,
                        "standard_angles": standard_angles,
                        "diffs": comparison.get("diffs", []),
                        "feedbacks": comparison.get("feedbacks", []),
                        "overall_score": score,
                        "best_score": best_score,
                        "session_phase": session_phase,
                    })

                    # ── 自动完成触发 ────────────────────
                    if good_streak >= AUTO_COMPLETE_STREAK:
                        duration = round(time.time() - session_start, 1) if session_start else 0
                        avg_score = round(total_score_sum / max(frame_count, 1), 1)
                        summary = self._generate_summary(
                            avg_score, best_score, feedback_counts, common_errors, duration
                        )
                        summary.insert(0, f"恭喜！您连续 {AUTO_COMPLETE_STREAK} 帧动作达标，自动完成学习！")

                        # 保存到数据库
                        record_id = self._save_learning_record(
                            user_id, current_action, current_view,
                            avg_score, best_score, frame_count,
                            angle_history, feedback_counts, summary, duration,
                        )

                        await ws.send_json({
                            "type": "learning_complete",
                            "record_id": record_id,
                            "total_score": avg_score,
                            "best_score": best_score,
                            "duration": duration,
                            "frame_count": frame_count,
                            "summary": summary,
                            "feedback_counts": feedback_counts,
                            "angle_history": angle_history[-60:],
                            "auto_triggered": True,
                        })
                        break  # 结束会话循环

                # ── switch_view ────────────────────────
                elif msg_type == "switch_view":
                    new_view = msg.get("view", "正面")
                    if current_action:
                        view_data = current_action.get("standard_keypoints", {}).get(new_view, {})
                        if view_data:
                            current_view = new_view
                            standard_angles = view_data.get("target_angles", {})
                            common_errors = current_action.get("common_errors", [])
                            # 切换视角后重新检测人体
                            good_streak = 0
                            session_phase = "waiting_for_body"
                            await ws.send_json({
                                "type": "view_switched",
                                "view": current_view,
                                "standard_angles": standard_angles,
                                "key_checks": view_data.get("key_checks", []),
                            })
                        else:
                            await ws.send_json({"type": "error", "message": f"该动作不支持「{new_view}」视角"})

                # ── finish ─────────────────────────────
                elif msg_type == "finish":
                    duration = round(time.time() - session_start, 1) if session_start else 0
                    avg_score = round(total_score_sum / max(frame_count, 1), 1)
                    summary = self._generate_summary(
                        avg_score, best_score, feedback_counts, common_errors, duration
                    )

                    # 保存到数据库
                    record_id = self._save_learning_record(
                        user_id, current_action, current_view,
                        avg_score, best_score, frame_count,
                        angle_history, feedback_counts, summary, duration,
                    )

                    await ws.send_json({
                        "type": "learning_complete",
                        "record_id": record_id,
                        "total_score": avg_score,
                        "best_score": best_score,
                        "duration": duration,
                        "frame_count": frame_count,
                        "summary": summary,
                        "feedback_counts": feedback_counts,
                        "angle_history": angle_history[-30:],
                        "auto_triggered": False,
                    })

                    # 重置状态
                    current_action = None
                    standard_angles = {}
                    session_start = None

        except Exception as e:
            logger.exception("[Learning WS] Error: %s", e)
            try:
                await ws.send_json({"type": "error", "message": f"会话异常: {str(e)}"})
            except Exception:
                pass

    def _compare_angles(
        self,
        user_angles: Dict[str, Optional[float]],
        standard_angles: Dict[str, Dict],
        common_errors: List[Dict],
        view: str,
    ) -> Dict:
        """
        对比用户角度与标准角度，返回差异和反馈

        Returns:
            {
                "diffs": [{"joint": "left_knee", "user": 85.0, "standard_optimal": 90, "diff": -5.0, "status": "good"}],
                "feedbacks": [{"name": "膝盖内扣", "severity": "warning", "message": "..."}],
                "overall_score": 85.0
            }
        """
        diffs = []
        feedbacks = []
        scores = []

        for joint_key, standard in standard_angles.items():
            user_val = user_angles.get(joint_key)
            if user_val is None:
                diffs.append({
                    "joint": joint_key,
                    "user": None,
                    "standard_optimal": standard.get("optimal", 90),
                    "standard_range": f"{standard.get('min', 0)}-{standard.get('max', 180)}",
                    "diff": None,
                    "status": "unknown",
                })
                continue

            optimal = standard.get("optimal", 90)
            min_val = standard.get("min", 0)
            max_val = standard.get("max", 180)
            diff = round(user_val - optimal, 1)

            # Status determination
            if min_val <= user_val <= max_val:
                status = "good"  # 达标 - green
                score = 100.0
            else:
                # Calculate how far outside the range
                if user_val < min_val:
                    overshoot = (min_val - user_val) / max(min_val, 1) * 100
                else:
                    overshoot = (user_val - max_val) / max(180 - max_val, 1) * 100

                if overshoot < 10:
                    status = "close"  # 接近 - yellow
                    score = 70.0
                elif overshoot < 25:
                    status = "warning"  # 偏差 - orange
                    score = 40.0
                else:
                    status = "bad"  # 严重偏差 - red
                    score = 10.0

            scores.append(score)

            diffs.append({
                "joint": joint_key,
                "user": round(user_val, 1),
                "standard_optimal": optimal,
                "standard_range": f"{min_val}-{max_val}",
                "diff": diff,
                "status": status,
            })

            # Check against common errors
            for error in common_errors:
                error_joint = error.get("joint", "")
                error_threshold = error.get("threshold", 999)

                if error_joint in joint_key or joint_key in error_joint:
                    if status in ("warning", "bad"):
                        # Generate specific feedback message
                        msg_template = error.get("feedback", "{name}: 偏差{value}°")
                        msg = msg_template.replace("{value}", str(abs(round(diff, 1))))
                        msg = msg.replace("{name}", error.get("name", ""))
                        feedbacks.append({
                            "name": error.get("name", ""),
                            "joint": joint_key,
                            "severity": status,
                            "message": msg,
                            "diff": abs(round(diff, 1)),
                        })

        overall_score = round(sum(scores) / max(len(scores), 1), 1) if scores else None

        # Deduplicate feedbacks (keep only one per name)
        seen_names = set()
        unique_feedbacks = []
        for fb in feedbacks:
            if fb["name"] not in seen_names:
                seen_names.add(fb["name"])
                unique_feedbacks.append(fb)

        return {
            "diffs": diffs,
            "feedbacks": unique_feedbacks,
            "overall_score": overall_score,
        }

    def _generate_summary(
        self,
        avg_score: float,
        best_score: float,
        feedback_counts: Dict[str, int],
        common_errors: List[Dict],
        duration: float,
    ) -> List[str]:
        """生成学习总结"""
        summary = []

        if avg_score >= 85:
            summary.append(f"动作标准度评分 {avg_score} 分，整体表现优秀！动作规范性良好。")
        elif avg_score >= 70:
            summary.append(f"动作标准度评分 {avg_score} 分，整体表现良好。部分细节可进一步优化。")
        elif avg_score >= 50:
            summary.append(f"动作标准度评分 {avg_score} 分，存在一些动作偏差，建议针对性改进。")
        else:
            summary.append(f"动作标准度评分 {avg_score} 分，动作规范性有待提高。建议从基础要领开始逐步练习。")

        if best_score > avg_score:
            summary.append(f"本次最佳帧得分 {best_score} 分，说明您有能力达到更高标准，保持最佳状态。")

        # Top frequent errors
        if feedback_counts:
            sorted_errors = sorted(feedback_counts.items(), key=lambda x: x[1], reverse=True)
            top_errors = sorted_errors[:3]
            for name, count in top_errors:
                error_def = next((e for e in common_errors if e.get("name") == name), None)
                if error_def:
                    clean_feedback = error_def.get('feedback', '请注意纠正').replace('{value}°', '').replace('{value}', '')
                    summary.append(f"「{name}」共出现 {count} 次——{clean_feedback}")

        summary.append(f"本次学习时长 {duration} 秒，继续坚持练习将有效改善动作质量。")
        return summary
