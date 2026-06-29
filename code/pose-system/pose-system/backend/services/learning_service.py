# -*- coding: utf-8 -*-
"""
标准学习服务 - 实时姿态对比与精细反馈
处理 WebSocket 连接，实现用户动作与标准动作的逐帧对比
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

        # Load action_library.json (58 actions, 10 families)
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

    # ---- accessors ----

    @property
    def actions(self) -> List[Dict]:
        return self._actions_list

    def get_by_name(self, name: str) -> Optional[Dict]:
        return self._actions_by_name.get(name)

    def get_by_id(self, action_id: str) -> Optional[Dict]:
        return self._actions_by_id.get(action_id)

    def get_standard_data(self, name: str) -> Optional[Dict]:
        """获取该动作在 standard_actions.json 中的标准角度数据（如有）"""
        return self._standard_data.get(name)

    def has_standard_angles(self, name: str) -> bool:
        """该动作是否有标准角度数据可用"""
        sd = self._standard_data.get(name)
        if not sd:
            return False
        return bool(sd.get("standard_keypoints"))

    def get_views(self, name: str) -> List[str]:
        """获取支持视角：优先标准数据，否则默认正面"""
        sd = self._standard_data.get(name)
        if sd and sd.get("views"):
            return sd["views"]
        return ["正面"]

    def get_families(self) -> List[str]:
        return sorted(self._families)

    def get_actions_by_family(self, family: str) -> List[Dict]:
        return [a for a in self._actions_list if a.get("family") == family]


class LearningService:
    """标准学习 REST 服务 — 提供统一动作数据查询"""

    def __init__(self):
        self.loader = UnifiedActionLoader()

    def list_learnable_actions(self) -> List[Dict]:
        """列出全部可学习的动作（58个）"""
        result = []
        for a in self.loader.actions:
            name = a["name"]
            sd = self.loader.get_standard_data(name)
            has_angles = self.loader.has_standard_angles(name)
            result.append({
                "name": name,
                "action_id": a.get("id", ""),
                "family": a.get("family", ""),
                "family_name": a.get("family_name", ""),
                "category": a.get("category", ""),
                "subcategory": a.get("subcategory", ""),
                "difficulty": a.get("difficulty", 1),
                "intensity": a.get("intensity", "MEDIUM"),
                "phases": a.get("phases", []),
                "target_body_parts": a.get("target_body_parts", []),
                "description": a.get("description", ""),
                "steps": a.get("steps", []),
                "cues": a.get("cues", []),
                "views": self.loader.get_views(name),
                "has_standard_angles": has_angles,
                "common_errors": (
                    [e.get("name") for e in sd.get("common_errors", [])]
                    if sd else []
                ),
            })
        return result

    def get_action_detail(self, name: str) -> Optional[Dict]:
        """获取动作详情（含标准角度、检查项）"""
        action = self.loader.get_by_name(name)
        if not action:
            return None
        sd = self.loader.get_standard_data(name)
        has_angles = self.loader.has_standard_angles(name)
        return {
            "name": name,
            "action_id": action.get("id", ""),
            "family": action.get("family", ""),
            "family_name": action.get("family_name", ""),
            "category": action.get("category", ""),
            "subcategory": action.get("subcategory", ""),
            "difficulty": action.get("difficulty", 1),
            "intensity": action.get("intensity", "MEDIUM"),
            "phases": action.get("phases", []),
            "target_body_parts": action.get("target_body_parts", []),
            "description": action.get("description", ""),
            "steps": action.get("steps", []),
            "cues": action.get("cues", []),
            "views": self.loader.get_views(name),
            "has_standard_angles": has_angles,
            "standard_keypoints": sd.get("standard_keypoints", {}) if sd else {},
            "common_errors": sd.get("common_errors", []) if sd else [],
            "contraindications": action.get("contraindications", {}),
        }

    def get_standard_angles(self, action_name: str, view: str) -> Dict[str, Any]:
        """获取指定动作在指定视角下的标准角度"""
        sd = self.loader.get_standard_data(action_name)
        if not sd:
            return {}
        view_data = sd.get("standard_keypoints", {}).get(view, {})
        return view_data.get("target_angles", {})


class RealtimeLearningService(BaseWebSocketHandler):
    """实时学习 WebSocket 服务 — 处理逐帧对比"""

    def __init__(self, db: Session):
        super().__init__(db)
        self.loader = UnifiedActionLoader()

    async def handle_session(self, ws: WebSocket, user_id: int):
        """
        处理标准学习 WebSocket 会话
        消息协议:
        - 客户端 → 服务端:
            {type: "start", action: "深蹲", view: "正面"}
            {type: "frame", data: "<base64_image>"}
            {type: "finish"}
        - 服务端 → 客户端:
            {type: "session_ready", action: {...}, standard_angles: {...}}
            {type: "comparison", angles: {...}, diffs: [...], feedbacks: [...], overall_score: 0-100}
            {type: "learning_complete", total_score: 0-100, summary: [...], duration: 30}
            {type: "error", message: "..."}
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

        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                msg_type = msg.get("type", "")

                if msg_type == "start":
                    action_name = msg.get("action", "")
                    current_view = msg.get("view", "正面")

                    if not action_name:
                        await ws.send_json({"type": "error", "message": "请指定学习动作"})
                        continue

                    action = self.loader.get_action(action_name)
                    if not action:
                        await ws.send_json({"type": "error", "message": f"未找到动作: {action_name}"})
                        continue

                    current_action = action
                    view_data = action.get("standard_keypoints", {}).get(current_view, {})
                    standard_angles = view_data.get("target_angles", {})
                    common_errors = action.get("common_errors", [])

                    session_start = time.time()
                    frame_count = 0
                    angle_history = []
                    total_score_sum = 0.0
                    best_score = 0.0
                    feedback_counts = {}

                    await ws.send_json({
                        "type": "session_ready",
                        "action": {
                            "name": action_name,
                            "category": action.get("category", ""),
                            "description": action.get("description", ""),
                            "video_url": action.get("video_url", ""),
                            "views": action.get("views", ["正面"]),
                        },
                        "current_view": current_view,
                        "standard_angles": standard_angles,
                        "key_checks": view_data.get("key_checks", []),
                        "instruction": f"请面对摄像头，跟随标准示范完成「{action_name}」动作",
                    })

                elif msg_type == "frame":
                    if not current_action or not standard_angles:
                        await ws.send_json({"type": "error", "message": "请先发送 start 消息"})
                        continue

                    kp_xy, kp_confs, frame = self.extract_keypoints_from_msg(msg)
                    if kp_xy is None:
                        await ws.send_json({
                            "type": "comparison",
                            "frame": frame_count,
                            "user_angles": {},
                            "standard_angles": standard_angles,
                            "diffs": [],
                            "feedbacks": [{"name": "未检测到人体", "severity": "error", "message": "请确保全身在摄像头范围内"}],
                            "overall_score": None,
                        })
                        continue

                    # Build (17, 3) array with x, y, confidence
                    full_kps = np.zeros((17, 3), dtype=np.float32)
                    full_kps[:, :2] = kp_xy
                    full_kps[:, 2] = kp_confs if kp_confs else np.ones(17)

                    # Compute user angles
                    user_angles = self.compute_angles(full_kps)

                    # Compare with standard
                    comparison = self._compare_angles(
                        user_angles, standard_angles, common_errors, current_view
                    )

                    frame_count += 1
                    if comparison.get("overall_score") is not None:
                        total_score_sum += comparison["overall_score"]
                        if comparison["overall_score"] > best_score:
                            best_score = comparison["overall_score"]

                    angle_history.append({
                        "frame": frame_count,
                        "angles": {k: round(v, 1) for k, v in user_angles.items() if v is not None},
                        "score": comparison.get("overall_score"),
                    })

                    for fb in comparison.get("feedbacks", []):
                        name = fb.get("name", "")
                        feedback_counts[name] = feedback_counts.get(name, 0) + 1

                    # Send comparison result
                    await ws.send_json({
                        "type": "comparison",
                        "frame": frame_count,
                        "user_angles": {k: round(v, 1) for k, v in user_angles.items() if v is not None},
                        "standard_angles": standard_angles,
                        "diffs": comparison.get("diffs", []),
                        "feedbacks": comparison.get("feedbacks", []),
                        "overall_score": comparison.get("overall_score"),
                        "best_score": best_score,
                    })

                elif msg_type == "switch_view":
                    new_view = msg.get("view", "正面")
                    if current_action:
                        view_data = current_action.get("standard_keypoints", {}).get(new_view, {})
                        if view_data:
                            current_view = new_view
                            standard_angles = view_data.get("target_angles", {})
                            common_errors = current_action.get("common_errors", [])
                            await ws.send_json({
                                "type": "view_switched",
                                "view": current_view,
                                "standard_angles": standard_angles,
                                "key_checks": view_data.get("key_checks", []),
                            })
                        else:
                            await ws.send_json({"type": "error", "message": f"该动作不支持「{new_view}」视角"})

                elif msg_type == "finish":
                    duration = round(time.time() - session_start, 1) if session_start else 0
                    avg_score = round(total_score_sum / max(frame_count, 1), 1)

                    # Generate summary
                    summary = self._generate_summary(
                        avg_score, best_score, feedback_counts, common_errors, duration
                    )

                    # Save learning record
                    record_id = None
                    try:
                        record = models.AssessmentRecord(
                            user_id=user_id,
                            balance_score=0,
                            flexibility_score=0,
                            upper_limb_score=0,
                            core_score=0,
                            symmetry_score=0,
                            overall_score=avg_score,
                            risk_level="low" if avg_score >= 70 else ("medium" if avg_score >= 40 else "high"),
                            posture_data=json.dumps({
                                "action": current_action.get("name") if current_action else "",
                                "view": current_view,
                            }, ensure_ascii=False),
                            movement_data=json.dumps({
                                "angle_history": angle_history[-50:],  # Keep last 50 frames
                            }, ensure_ascii=False),
                            rom_data=json.dumps({
                                "best_score": best_score,
                                "frame_count": frame_count,
                            }, ensure_ascii=False),
                            muscle_findings=json.dumps({
                                "feedback_counts": feedback_counts,
                            }, ensure_ascii=False),
                            report_data=json.dumps({
                                "summary": summary,
                                "duration": duration,
                                "average_score": avg_score,
                                "best_score": best_score,
                            }, ensure_ascii=False),
                        )
                        self.db.add(record)
                        self.db.commit()
                        self.db.refresh(record)
                        record_id = record.id
                    except Exception as e:
                        logger.warning("[Learning] DB save error: %s", e)
                        try:
                            self.db.rollback()
                        except:
                            pass

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
                    })

                    # Reset state
                    current_action = None
                    standard_angles = {}
                    session_start = None

        except Exception as e:
            logger.exception("[Learning WS] Error: %s", e)
            try:
                await ws.send_json({"type": "error", "message": f"会话异常: {str(e)}"})
            except:
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
                    "standard_optimal": standard.get("optimal", 0),
                    "standard_range": f"{standard.get('min', 0)}-{standard.get('max', 0)}",
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
                    summary.append(f"「{name}」共出现 {count} 次——{error_def.get('feedback', '请注意纠正').replace('{value}°', '')}")

        summary.append(f"本次学习时长 {duration} 秒，继续坚持练习将有效改善动作质量。")
        return summary
