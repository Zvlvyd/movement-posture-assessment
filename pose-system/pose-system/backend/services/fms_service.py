from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from backend.database import models
from models.fms.scoring import FMSScoringEngine
from models.fms.radar_report import RadarReport
from models.fms.problem_tagger import ProblemTagger
from backend.schemas.business import FMSSubmitRequest, FMSResultResponse
from backend.logger import get_logger

logger = get_logger(__name__)


def build_fms_analysis(score_map: dict) -> dict:
    """根据五项得分生成富文本分析数据，供 WebSocket 和 REST API 共用。"""
    from models.fms.scoring import FMSScoringEngine, Score
    import json as _json, os as _os

    dim_labels = {"balance": "平衡能力", "flexibility": "下肢柔韧性", "upper_limb": "肩关节活动度", "core": "核心稳定性", "symmetry": "左右对称性"}
    dim_details = {
        "balance": "闭眼单腿站立时长", "flexibility": "过头深蹲膝盖弯曲角度",
        "upper_limb": "背后双手距离", "core": "平板支撑时长", "symmetry": "弓步蹲左右膝角度差",
    }
    dim_advice = {
        "balance": ("单腿站立训练", "从扶墙开始，逐步过渡到闭眼单腿站立，每天3组"),
        "flexibility": ("动态拉伸", "训练前后充分拉伸股四头肌和腘绳肌，泡沫轴放松"),
        "upper_limb": ("肩关节活动度训练", "肩部环绕、背后扣手拉伸、弹力带肩部拉伸"),
        "core": ("核心力量训练", "平板支撑、鸟狗式、死虫式，逐步增加时长"),
        "symmetry": ("单侧纠正训练", "弱侧加练，保加利亚分腿蹲、单腿臀桥"),
    }
    dim_problem_detail = {
        "balance": "平衡能力不足意味着本体感觉和踝关节稳定性较差，日常活动中容易扭伤脚踝，运动中变向能力受限，老年人则有较高跌倒风险。",
        "flexibility": "下肢柔韧性不足会导致深蹲时膝盖和腰部代偿受力，长期可能引发膝痛或腰痛，也限制运动表现。",
        "upper_limb": "肩关节活动度受限通常与圆肩、驼背体态相关，会导致肩峰撞击风险增加，上肢推拉动作受限，长期可能发展为肩周炎。",
        "core": "核心稳定性不足意味着腰椎缺乏有效支撑，久坐或负重时容易腰酸背痛，也会影响四肢力量的传递效率。",
        "symmetry": "左右不对称说明存在明显的单侧力量或柔韧性差异，是运动损伤的前兆信号，需要有针对性强化弱侧。",
    }
    # 从动作库匹配推荐动作
    action_recs = {}
    try:
        lib_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "models", "prescription_v2", "action_library.json")
        with open(lib_path, "r", encoding="utf-8") as f:
            actions = _json.load(f).get("actions", [])
        dim_keywords = {
            "balance": ["平衡", "单腿", "踝", "站立"],
            "flexibility": ["拉伸", "髋", "腘绳", "股四头", "深蹲"],
            "upper_limb": ["肩", "俯卧撑", "推", "拉", "旋转"],
            "core": ["核心", "平板", "腹", "桥", "支撑"],
            "symmetry": ["弓步", "单侧", "分腿", "臀桥"],
        }
        for dim, keywords in dim_keywords.items():
            matched = []
            for a in actions:
                text = a.get("name", "") + a.get("category", "") + a.get("description", "") + " ".join(a.get("target_body_parts", []))
                score = sum(1 for kw in keywords if kw in text)
                if score > 0:
                    matched.append((score, a))
            matched.sort(key=lambda x: (-x[0], x[1].get("difficulty", 99)))
            action_recs[dim] = [m[1] for m in matched[:3]]
    except Exception:
        pass

    engine = FMSScoringEngine()
    score_list = []
    for dim in ["balance", "flexibility", "upper_limb", "core", "symmetry"]:
        s = score_map.get(dim)
        if s is not None:
            score_list.append({"dimension": dim, "label": dim_labels.get(dim, dim), "score": s,
                "detail": dim_details.get(dim, ""), "advice": dim_advice.get(dim, ("", "")),
                "problem_detail": dim_problem_detail.get(dim, ""),
                "recommended_actions": [
                    {"name": a["name"], "difficulty": a.get("difficulty", 1),
                     "category": a.get("category", ""), "description": a.get("description", "")}
                    for a in action_recs.get(dim, [])
                ]})

    score_objs = [Score(s["dimension"], s["score"], s["detail"]) for s in score_list]
    problem_tags = ProblemTagger.tag(score_objs) if ProblemTagger else []
    for tag in problem_tags:
        dim = tag["dimension"]
        tag["name"] = dim_labels.get(dim, dim)
        tag["advice"] = dim_advice.get(dim, ("", ""))
        tag["problem_detail"] = dim_problem_detail.get(dim, "")
        tag["recommended_actions"] = [
            {"name": a["name"], "difficulty": a.get("difficulty", 1), "category": a.get("category", ""), "description": a.get("description", "")}
            for a in action_recs.get(dim, [])
        ]
    recommendations = engine.get_recommendations(score_objs)
    return {"scores": score_list, "problem_tags": problem_tags, "recommendations": recommendations}


class FMSService:
    def __init__(self, db: Session):
        self.db = db
        self.engine = FMSScoringEngine()

    def process_screening(self, user_id: int, data: FMSSubmitRequest):
        scores = []
        if data.balance_duration is not None:
            scores.append(self.engine.score_balance(data.balance_duration))
        if data.flexibility_depth is not None:
            scores.append(self.engine.score_flexibility(data.flexibility_depth, data.flexibility_trunk or 0, data.flexibility_arm or 1.0))
        if data.upper_limb_distance is not None:
            scores.append(self.engine.score_upper_limb(data.upper_limb_distance))
        if data.core_duration is not None:
            scores.append(self.engine.score_core(data.core_duration))
        if data.symmetry_left is not None and data.symmetry_right is not None:
            scores.append(self.engine.score_symmetry(data.symmetry_left, data.symmetry_right))
        overall = self.engine.compute_overall(scores)
        risk_level = self.engine.get_risk_level(overall, scores)
        record = models.FMSRecord(user_id=user_id, balance_score=next((s.score for s in scores if s.dimension == "balance"), None), flexibility_score=next((s.score for s in scores if s.dimension == "flexibility"), None), upper_limb_score=next((s.score for s in scores if s.dimension == "upper_limb"), None), core_score=next((s.score for s in scores if s.dimension == "core"), None), symmetry_score=next((s.score for s in scores if s.dimension == "symmetry"), None), overall_score=overall, risk_level=risk_level)
        self.db.add(record); self.db.commit(); self.db.refresh(record)
        radar = RadarReport.generate(scores, overall, risk_level)
        tags = ProblemTagger.tag(scores)
        result = FMSResultResponse.model_validate(record)
        result.radar_data = radar; result.problem_tags = tags
        return result

    def get_user_records(self, user_id: int):
        return self.db.query(models.FMSRecord).filter(models.FMSRecord.user_id == user_id).order_by(models.FMSRecord.test_date.desc()).all()

    def get_record_detail(self, record_id: int, user_id: int):
        record = self.db.query(models.FMSRecord).filter(models.FMSRecord.id == record_id, models.FMSRecord.user_id == user_id).first()
        if not record: raise HTTPException(status_code=404, detail="Record not found")
        result = FMSResultResponse.model_validate(record)
        # 附加富文本分析
        enriched = build_fms_analysis({
            "balance": record.balance_score,
            "flexibility": record.flexibility_score,
            "upper_limb": record.upper_limb_score,
            "core": record.core_score,
            "symmetry": record.symmetry_score,
        })
        for key, value in enriched.items():
            setattr(result, key, value)
        return result

import json, math, os, time
from typing import Dict, List, Optional, Any
from fastapi import WebSocket
from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np

from models.angle_calculator import AngleCalculator
from models.posture_analyzer import PostureAnalyzer
from config.settings import settings
from backend.services.base import BaseWebSocketHandler

import threading

# 全局存储：跨请求共享单动作视频处理结果
# key: "{user_id}_{test_index}", value: dict with score, data, completed, best_keypoints
_single_test_results_global: Dict[str, dict] = {}
_single_test_results_lock = threading.Lock()


class RealtimeFMSService(BaseWebSocketHandler):
    def __init__(self, db: Session):
        super().__init__(db)
        self.engine = FMSScoringEngine()

    async def handle_session(self, ws: WebSocket, user_id: int):
# ws.accept() already called in router
        state = FMSState()
        try:
            while True:
                raw = await ws.receive_text()
                msg = json.loads(raw)
                mt = msg.get("type")
                if mt == "start":
                    state.reset()
                    # 提前加载 YOLO 模型，避免首帧延迟
                    from models.engine import model_manager
                    model_manager.preload()
                    t = state.tests[0]
                    t["status"] = "awaiting_user"
                    await ws.send_json({"type":"test_ready","test":0,"name":t["name"],"instruction":t["instruction"],"total_tests":5})
                elif mt == "skip_test":
                    test = state.current_test()
                    if test:
                        test["status"] = "skipped"
                        test["completed"] = True
                        test["score"] = 0
                        test["data"] = {"skipped": True}
                    await ws.send_json({"type": "test_skipped", "test": state.current_test_idx})
                elif mt == "start_test":
                    test = state.current_test()
                    if test and test["status"] == "awaiting_user":
                        test["status"] = "ready"
                elif mt == "frame":
                    test = state.current_test()
                    if not test:
                        continue
                    b64 = msg.get("image","")
                    if not b64:
                        continue
                    try:
                        frame = self.decode_frame(b64)
                        if frame is None:
                            continue
                        kp_xy, kp_confs = self.extract_keypoints(frame)
                    except Exception as e:
                        logger.warning("[FMS] YOLO extraction error: %s", e)
                        try:
                            await ws.send_json({"type":"frame_result","test_idx":state.current_test_idx,"keypoints":[],"fms_status":"no_person"})
                        except:
                            pass
                        continue

                    try:
                        if kp_xy is None:
                            eval_res = {"type":"frame_result","test_idx":state.current_test_idx,"keypoints":[],"fms_status":"no_person"}
                            await ws.send_json(eval_res)
                            continue

                        confs = kp_confs if kp_confs is not None else [1.0]*len(kp_xy)
                        keypoints_list = [{"keypoints": kp_xy.tolist(), "confidences": confs}]
                        eval_res = {"type":"frame_result","test_idx":state.current_test_idx,"keypoints": keypoints_list}

                        kps = np.column_stack([kp_xy, confs])
                        # Store best keypoints for posture analysis
                        if state.best_keypoints is None:
                            state.best_keypoints = kp_xy.tolist()
                        angles = self.compute_angles(kps)
                        test_idx = state.current_test_idx

                        # awaiting_user 状态：只返回关键点用于骨架显示，不运行评估
                        if test["status"] == "awaiting_user":
                            eval_res["fms_status"] = "observing"
                            await ws.send_json(eval_res)
                            continue

                        # 仅在 ready/running/running_left/running_right 状态运行评估；
                        # running_left/running_right 用于弓步蹲左右分步评估
                        if test["status"] in ("ready", "running", "running_left", "running_right"):
                            evaluation = {}
                            if test_idx == 0:
                                evaluation = self._eval_balance(state, angles, kps)
                            elif test_idx == 1:
                                evaluation = self._eval_squat(state, angles, kps)
                            elif test_idx == 2:
                                evaluation = self._eval_shoulder(state, angles, kps)
                            elif test_idx == 3:
                                evaluation = self._eval_plank(state, angles, kps)
                            elif test_idx == 4:
                                evaluation = self._eval_symmetry(state, angles, kps)
                            eval_res.update(evaluation)
                        else:
                            eval_res["fms_status"] = "observing"

                        await ws.send_json(eval_res)
                    except Exception as e:
                        import traceback
                        logger.warning("[FMS] Frame processing error: %s\n%s", e, traceback.format_exc())
                        try:
                            await ws.send_json({"type":"frame_result","test_idx":state.current_test_idx,"keypoints":keypoints_list if 'keypoints_list' in dir() else [],"fms_status":"error","error":str(e)})
                        except:
                            pass
                elif mt == "next_test":
                    logger.info("[FMS] next_test received, idx=%s", state.current_test_idx)
                    cur_test = state.current_test()
                    # 如果当前测试在运行中或等待开始，先结束并返回分数，不推进到下一个
                    if cur_test and not cur_test.get("completed") and cur_test.get("status") in ("running", "ready", "running_left", "running_right"):
                        cur_test["status"] = "done"
                        cur_test["completed"] = True
                        tidx = state.current_test_idx
                        if tidx == 0:  # 平衡：有效用时（扣除暂停时间）
                            start = cur_test.get("start_time", 0)
                            if start > 0:
                                raw_dur = time.time() - start
                                paused_dur = cur_test.get("paused_duration", 0)
                                paused_at = cur_test.get("paused_at")
                                if paused_at is not None:
                                    paused_dur += time.time() - paused_at
                                dur_val = max(0, raw_dur - paused_dur)
                                if dur_val > 0:
                                    cur_test["data"] = {"duration": round(dur_val, 1)}
                                    cur_test["score"] = round(self.engine.score_balance(dur_val).score, 1)
                                else:
                                    cur_test["score"] = 0
                            else:
                                cur_test["score"] = 0
                        elif tidx == 1:  # 深蹲
                            vals = cur_test.get("knee_vals", [])
                            if vals:
                                avg_k = sum(vals) / len(vals)
                                cur_test["data"] = {"depth_angle": round(avg_k, 1)}
                                cur_test["score"] = round(self.engine.score_flexibility(avg_k, 0, 1.0).score, 1)
                            else:
                                cur_test["score"] = 0
                        elif tidx == 2:  # 肩
                            dists = cur_test.get("dists", [])
                            if dists:
                                avg_d = sum(dists) / len(dists)
                                cur_test["data"] = {"hand_distance": round(avg_d, 1)}
                                cur_test["score"] = round(self.engine.score_upper_limb(avg_d).score, 1)
                            else:
                                cur_test["score"] = 0
                        elif tidx == 3:  # 平板：有效用时（扣除暂停时间）
                            start = cur_test.get("start_time", 0)
                            if start > 0:
                                raw_dur = time.time() - start
                                paused_dur = cur_test.get("paused_duration", 0)
                                paused_at = cur_test.get("paused_at")
                                if paused_at is not None:
                                    paused_dur += time.time() - paused_at
                                dur_val = max(0, raw_dur - paused_dur)
                                if dur_val > 0:
                                    cur_test["data"] = {"duration": round(dur_val, 1)}
                                    cur_test["score"] = round(self.engine.score_core(dur_val).score, 1)
                                else:
                                    cur_test["score"] = 0
                            else:
                                cur_test["score"] = 0
                        elif tidx == 4:  # 对称（弓步蹲）
                            ls = cur_test.get("left_score")
                            rs = cur_test.get("right_score")
                            if ls is not None and rs is not None:
                                cur_test["data"] = {"left_score": round(ls, 1), "right_score": round(rs, 1)}
                                cur_test["score"] = round(self.engine.score_symmetry(ls, rs).score, 1)
                            else:
                                vals_l = cur_test.get("cl", []); vals_r = cur_test.get("cr", [])
                                # 如果左右两侧都没有采集到任何有效数据 → 0 分
                                if not vals_l and not vals_r:
                                    cur_test["score"] = 0
                                    cur_test["data"] = {"left_score": 0, "right_score": 0, "warning": "未检测到有效的弓步蹲动作"}
                                else:
                                    ls = max(0, 100 - abs(90 - sum(vals_l)/len(vals_l))) if vals_l else 0
                                    rs = max(0, 100 - abs(90 - sum(vals_r)/len(vals_r))) if vals_r else 0
                                    cur_test["left_score"] = ls; cur_test["right_score"] = rs
                                    cur_test["data"] = {"left_score": round(ls, 1), "right_score": round(rs, 1)}
                                    cur_test["score"] = round(self.engine.score_symmetry(ls, rs).score, 1)
                        logger.info("[FMS] Test %s manually completed, score=%s", tidx, cur_test.get('score'))
                        # 发送完成结果给前端展示分数，不推进
                        comp_data = cur_test.get("data", {}) or {}
                        result = {"type":"frame_result","test_idx":tidx,"fms_status":"completed","score":cur_test.get("score",0)}
                        result.update(comp_data)
                        await ws.send_json(result)
                    elif cur_test and cur_test.get("completed"):
                        # 测试已完成（或已跳过），推进到下一个
                        logger.info("[FMS] advancing from completed test %s", state.current_test_idx)
                        idx = state.advance_to_next()
                        if idx >= 0:
                            t = state.current_test()
                            t["status"] = "awaiting_user"
                            await ws.send_json({"type":"test_ready","test":idx,"name":t["name"],"instruction":t["instruction"],"total_tests":5})
                        else:
                            await self._send_final_result(ws, state, user_id)
                    else:
                        logger.warning("[FMS] next_test unhandled: cur_test=%s status=%s completed=%s",
                                       cur_test is not None,
                                       cur_test.get("status") if cur_test else "None",
                                       cur_test.get("completed") if cur_test else "None")
                elif mt == "finish":
                    logger.info("[FMS] finish received")
                    await self._send_final_result(ws, state, user_id)
        except BaseException as e:
            logger.exception("[FMS] WebSocket session error: %s", e)
            try:
                await ws.send_json({"type":"error","message":f"服务器内部错误: {str(e)}"})
            except:
                pass
            try:
                await ws.close(code=1011)
            except:
                pass

    async def _send_final_result(self, ws, state, user_id: int):
        try:
            tests_completed = [t for t in state.tests if t.get("completed")]
            tests_skipped = [t for t in state.tests if t.get("status") == "skipped"]
            
            score_map = {"balance": None, "flexibility": None, "upper_limb": None, "core": None, "symmetry": None}
            score_list = []
            for t in tests_completed:
                d = t.get("data", {}) or {}
                idx = t.get("idx", 0)
                sc = t.get("score", 0)
                dim_map = {0: "balance", 1: "flexibility", 2: "upper_limb", 3: "core", 4: "symmetry"}
                dim = dim_map.get(idx, "unknown")
                score_map[dim] = sc
                score_list.append({"dimension": dim, "label": dim, "score": sc})
            
            scores_only = [s["score"] for s in score_list if s["score"] is not None]
            overall = round(sum(scores_only) / len(scores_only), 1) if scores_only else 0
            
            if overall >= 70: risk = "low"
            elif overall >= 40: risk = "medium"
            else: risk = "high"
            
            record_id = None
            try:
                from backend.database import models as db_models
                record = db_models.FMSRecord(
                    user_id=user_id,
                    balance_score=score_map.get("balance"),
                    flexibility_score=score_map.get("flexibility"),
                    upper_limb_score=score_map.get("upper_limb"),
                    core_score=score_map.get("core"),
                    symmetry_score=score_map.get("symmetry"),
                    overall_score=overall,
                    risk_level=risk,
                    test_date=datetime.utcnow(),
                )
                self.db.add(record)
                self.db.commit()
                self.db.refresh(record)
                record_id = record.id
                logger.info("[FMS] Saved record id=%s user=%s score=%s", record_id, user_id, overall)
            except Exception as e:
                import traceback
                logger.exception("[FMS] DB save failed: %s", e)
                try: self.db.rollback()
                except: pass
            
            # Run posture analysis
            posture_report = {}
            if state.best_keypoints:
                try:
                    from models.posture_analyzer import PostureAnalyzer
                    analyzer = PostureAnalyzer()
                    measurements = analyzer.analyze_from_keypoints(state.best_keypoints)
                    posture_report = analyzer.generate_report(measurements, score_list)
                    logger.info("[FMS] Posture: %s problems", len(posture_report.get('problems', [])))
                except Exception as e:
                    logger.warning("[FMS] Posture analysis error: %s", e)

            # ── 生成详细问题标签和建议 ──
            analysis = build_fms_analysis(score_map)

            # 姿势分析问题
            posture_problems = posture_report.get("problems", []) if posture_report else []

            result = {
                "type": "fms_result",
                "overall_score": overall,
                "risk_level": risk,
                "record_id": record_id,
                "completed_count": len(tests_completed),
                "skipped_count": len(tests_skipped),
                "scores": analysis["scores"],
                "problem_tags": analysis["problem_tags"],
                "recommendations": analysis["recommendations"],
                "posture_problems": [
                    {"name": p.get("name", ""), "severity": p.get("severity", "mild"), "detail": p.get("detail", str(p))}
                    for p in posture_problems
                ],
            }
            await ws.send_json(result)
        except Exception as e:
            import traceback
            logger.exception("[FMS] final result error: %s", e)
            try:
                await ws.send_json({"type":"fms_result","overall_score":0,"risk_level":"unknown","scores":[],"error":str(e)})
            except:
                pass

    def _eval_balance(self, state, angles, kps):
        """闭眼单腿站立 — 全身检测 + trunk_tilt ≤ 5° 时计时，否则暂停"""
        t = state.current_test()
        valid_kp = sum(1 for k in kps if len(k) > 2 and k[2] >= 0.3 and k[0] > 0 and k[1] > 0)
        if valid_kp < 7:
            if t["status"] == "ready":
                return {"fms_status":"ready","guidance":"请全身进入摄像头范围"}
            if t["status"] == "running":
                now = time.time()
                if t.get("paused_at") is None:
                    t["paused_at"] = now
                effective_dur = (now - t["start_time"]) - t.get("paused_duration", 0) - (now - t["paused_at"])
                return {"fms_status":"running","duration":round(max(0, effective_dur),1),"guidance":"未检测到完整人体"}
            return {}

        trunk_tilt = angles.get('trunk_tilt')

        if t["status"] == "ready":
            if trunk_tilt is not None and trunk_tilt <= 5.0:
                t["status"] = "running"
                t["start_time"] = time.time()
                t["paused_at"] = None
                return {"fms_status":"started"}
            return {"fms_status":"ready","guidance":"请抬起一只脚，躯干保持直立"}

        if t["status"] != "running":
            return {}

        now = time.time()
        paused_at = t.get("paused_at")
        if trunk_tilt is not None and trunk_tilt <= 5.0:
            if paused_at is not None:
                t["paused_duration"] = t.get("paused_duration", 0) + (now - paused_at)
                t["paused_at"] = None
            effective_dur = (now - t["start_time"]) - t.get("paused_duration", 0)
            return {"fms_status":"running","duration":round(effective_dur,1)}
        else:
            if paused_at is None:
                t["paused_at"] = now
            effective_dur = (now - t["start_time"]) - t.get("paused_duration", 0) - (now - t["paused_at"])
            return {"fms_status":"running","duration":round(max(0, effective_dur),1),"guidance":"躯干倾斜过大，请保持直立！"}

    def _eval_squat(self, state, angles, kps):
        t = state.current_test()
        knee = angles.get("left_knee") or angles.get("right_knee") or 180
        if t["status"] == "ready":
            t["status"] = "running"; t["knee_vals"] = []
            return {"fms_status":"started"}
        if knee < 120:
            t["knee_vals"].append(knee)
            if knee < 90:
                t["status"] = "done"; t["completed"] = True
                avg = sum(t["knee_vals"])/len(t["knee_vals"])
                t["data"] = {"depth_angle": round(avg,1)}
                t["score"] = round(self.engine.score_flexibility(avg, 0, 1.0).score,1)
                return {"fms_status":"completed","depth_angle":round(avg,1),"score":t["score"]}
            return {"fms_status":"running","depth_angle":round(knee,1)}
        return {"fms_status":"running"}

    def _eval_shoulder(self, state, angles, kps):
        t = state.current_test()
        if t["status"] == "ready":
            t["status"] = "running"; t["poses"] = 0; t["dists"] = []
            return {"fms_status":"started"}
        ls = kps[5][:2] if len(kps)>5 else [0,0]
        rs = kps[6][:2] if len(kps)>6 else [0,0]
        lw = kps[9][:2] if len(kps)>9 else [0,0]
        rw = kps[10][:2] if len(kps)>10 else [0,0]

        left_behind = lw[1] > ls[1] + 20 if lw[1]>0 and ls[1]>0 else False
        right_behind = rw[1] > rs[1] + 20 if rw[1]>0 and rs[1]>0 else False
        any_behind = left_behind or right_behind

        # 用肩宽作为参考尺，像素→厘米
        shoulder_width_px = float(np.linalg.norm(np.array(ls[:2]) - np.array(rs[:2]))) if ls[0] > 0 and rs[0] > 0 else 200
        px_to_cm = 38.0 / max(shoulder_width_px, 1)

        if any_behind:
            t["poses"] += 1
            if lw[0] > 0 and lw[1] > 0 and rw[0] > 0 and rw[1] > 0:
                dist_px = float(np.linalg.norm(np.array(lw[:2]) - np.array(rw[:2])))
                dist_cm = round(dist_px * px_to_cm, 1)
            else:
                dist_cm = 60.0
            t["dists"].append(dist_cm)
            if t["poses"] >= 5:
                t["status"] = "done"; t["completed"] = True
                best_dists = sorted(t["dists"])[:max(3, len(t["dists"]) // 3)]
                avg = sum(best_dists) / len(best_dists)
                t["data"] = {"hand_distance": round(avg,1)}
                t["score"] = round(self.engine.score_upper_limb(avg).score,1)
                return {"fms_status":"completed","hand_distance":round(avg,1),"score":t["score"]}
            return {"fms_status":"running","hand_distance":round(dist_cm,1)}
        return {"fms_status":"running"}

    def _eval_plank(self, state, angles, kps):
        """平板支撑 — 全身检测 + hip_angle 在 [160°, 185°] 时计时，否则暂停"""
        t = state.current_test()
        valid_kp = sum(1 for k in kps if len(k) > 2 and k[2] >= 0.3 and k[0] > 0 and k[1] > 0)
        if valid_kp < 7:
            if t["status"] == "ready":
                return {"fms_status":"ready","guidance":"请全身进入摄像头范围"}
            if t["status"] == "running":
                now = time.time()
                if t.get("paused_at") is None:
                    t["paused_at"] = now
                effective_dur = (now - t["start_time"]) - t.get("paused_duration", 0) - (now - t["paused_at"])
                return {"fms_status":"running","duration":round(max(0, effective_dur),1),"guidance":"未检测到完整人体"}
            return {}

        hip = angles.get('left_hip') or angles.get('right_hip')

        if t["status"] == "ready":
            if hip is not None and 160.0 <= hip <= 185.0:
                t["status"] = "running"; t["start_time"] = time.time()
                t["paused_at"] = None
                return {"fms_status":"started"}
            return {"fms_status":"ready","guidance":"请进入平板支撑姿势，身体保持一条直线"}

        if t["status"] != "running":
            return {}

        now = time.time()
        paused_at = t.get("paused_at")
        if hip is not None and 160.0 <= hip <= 185.0:
            if paused_at is not None:
                t["paused_duration"] = t.get("paused_duration", 0) + (now - paused_at)
                t["paused_at"] = None
            effective_dur = (now - t["start_time"]) - t.get("paused_duration", 0)
            return {"fms_status":"running","duration":round(effective_dur,1)}
        else:
            if paused_at is None:
                t["paused_at"] = now
            effective_dur = (now - t["start_time"]) - t.get("paused_duration", 0) - (now - t["paused_at"])
            return {"fms_status":"running","duration":round(max(0, effective_dur),1),"guidance":"臀部下沉或抬高，请保持身体水平！"}

    def _eval_symmetry(self, state, angles, kps):
        t = state.current_test()
        kl = angles.get("left_knee",180) or 180
        kr = angles.get("right_knee",180) or 180
        if t["status"] == "ready":
            t["status"] = "running_left"; t["cl"]=[]; t["cr"]=[]
            return {"fms_status":"started","side":"left"}
        if t["status"] == "running_left":
            if kl < 120:
                t["cl"].append(kl)
                t["status"] = "running_right"
                t["left_score"] = max(0, 100 - abs(90 - kl))
                return {"fms_status":"step_complete","side":"left","score":round(t["left_score"],1)}
            return {"fms_status":"running","side":"left"}
        if t["status"] == "running_right":
            if kr < 120:
                t["cr"].append(kr)
                t["right_score"] = max(0, 100 - abs(90 - kr))
                t["status"] = "done"; t["completed"] = True
                t["data"] = {"left_score":round(t["left_score"],1),"right_score":round(t["right_score"],1)}
                t["score"] = round(self.engine.score_symmetry(t["left_score"],t["right_score"]).score,1)
                return {"fms_status":"completed","left_score":round(t["left_score"],1),"right_score":round(t["right_score"],1),"score":t["score"]}
            return {"fms_status":"running","side":"right"}
        return {}


class FMSState:
    def __init__(self):
        self.current_test_idx = 0
        self.best_keypoints = None
        self.tests = [
            {"idx":0,"name":"闭眼单腿站立","instruction":"双手叉腰，闭眼，单腿站立保持平衡（站立越久分数越高，满分60秒）","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":1,"name":"过头深蹲","instruction":"双手举过头顶，缓慢下蹲至最低点再站起（膝盖弯曲角度越小分数越高）","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":2,"name":"肩活动度","instruction":"一手从肩上方向后、另一手从腰后方向前，双手背后相触（双手距离越近分数越高）","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":3,"name":"平板支撑","instruction":"俯卧，用前臂和脚尖支撑身体，保持成一条直线（坚持越久分数越高，满分90秒）","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":4,"name":"弓步蹲","instruction":"双手叉腰，向前迈出弓步蹲，左右交替完成（左右角度越对称分数越高）","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
        ]

    def current_test(self):
        if self.current_test_idx < len(self.tests):
            return self.tests[self.current_test_idx]
        return None

    def reset(self):
        self.__init__()

    def advance_to_next(self):
        for i in range(self.current_test_idx + 1, len(self.tests)):
            if not self.tests[i].get("completed"):
                self.current_test_idx = i
                return i
        return -1


class VideoFMSService:
    """处理上传的 FMS 筛查视频，逐帧分析并返回评估结果"""

    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()
        self.engine = FMSScoringEngine()
        self.yolo = None

    def _get_yolo(self):
        if self.yolo is None:
            from models.yolo_pose_engine import YOLOPoseEngine
            from config.settings import settings
            self.yolo = YOLOPoseEngine(model_path=settings.MODEL_PATH, device=settings.DEVICE)
        return self.yolo

    async def process_video(self, video_path: str, user_id: int) -> dict:
        """处理视频文件，逐帧分析 5 项 FMS 测试"""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            cap.release()
            raise Exception("视频文件为空")

        logger.info("[VideoFMS] Processing video: %s frames, %.1f FPS", total_frames, fps)

        # 全视频模式不跳帧（用户主要用单动作上传）
        frame_skip = 1
        logger.info("[VideoFMS] Full-video mode: no frame skip")

        state = FMSState()
        yolo = self._get_yolo()
        frame_count = 0
        real_frame_count = 0
        best_keypoints_all = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if real_frame_count % frame_skip != 0:
                real_frame_count += 1
                continue

            persons, _ = yolo.process_frame(frame)
            if not persons:
                frame_count += 1
                real_frame_count += 1
                continue

            person = persons[0]
            kps = np.array(person["keypoints"])
            bbox = person.get("bbox")
            if bbox and (state.best_keypoints is None or (bbox[3] - bbox[1]) > 100):
                state.best_keypoints = person["keypoints"]
                best_keypoints_all.append(person["keypoints"])

            angles = self.angle_calc.compute_all_angles(kps)
            test_idx = state.current_test_idx
            test = state.current_test()
            if not test or test.get("completed"):
                frame_count += 1
                continue

            if test_idx == 0:
                self._eval_balance_video(state, angles, kps, real_frame_count, fps)
            elif test_idx == 1:
                self._eval_squat_video(state, angles, kps)
            elif test_idx == 2:
                self._eval_shoulder_video(state, angles, kps)
            elif test_idx == 3:
                self._eval_plank_video(state, angles, kps, real_frame_count, fps)
            elif test_idx == 4:
                self._eval_symmetry_video(state, angles, kps)

            if test.get("completed"):
                logger.info("[VideoFMS] Test %s completed, score=%s", test_idx, test.get('score'))
                next_idx = state.advance_to_next()
                if next_idx < 0:
                    break

            frame_count += 1
            real_frame_count += 1
            if real_frame_count % (30 * frame_skip) == 0:
                logger.debug("[VideoFMS] Progress: %s/%s real frames", real_frame_count, total_frames)

        # 视频播放完毕，若当前测试仍在运行中则根据累计时间计分
        cur = state.current_test()
        if cur and not cur.get("completed") and cur.get("status") == "running":
            tidx = state.current_test_idx
            if tidx == 0:
                dur_frames = real_frame_count - cur.get("start_frame", 0)
                dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
                cur["data"] = {"duration": round(dur_seconds, 1)}
                cur["score"] = round(self.engine.score_balance(dur_seconds).score, 1)
            elif tidx == 3:
                dur_frames = real_frame_count - cur.get("start_frame", 0)
                dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
                cur["data"] = {"duration": round(dur_seconds, 1)}
                cur["score"] = round(self.engine.score_core(dur_seconds).score, 1)
            cur["status"] = "done"
            cur["completed"] = True
            logger.info("[VideoFMS] Test %s ended by video end, score=%s", tidx, cur.get("score"))

        cap.release()
        logger.info("[VideoFMS] Video processing done, processed %s frames", frame_count)

        return self._build_result(state, user_id, best_keypoints_all)

    def _eval_balance_video(self, state, angles, kps, frame_count, fps):
        test = state.current_test()
        left_ankle = kps[15][:2] if len(kps) > 15 else [0, 0]
        right_ankle = kps[16][:2] if len(kps) > 16 else [0, 0]
        ankle_diff = abs(left_ankle[1] - right_ankle[1])
        foot_lifted = ankle_diff > 30

        if test["status"] == "pending" or test["status"] == "ready":
            if foot_lifted:
                test["status"] = "running"
                test["start_frame"] = frame_count
                test["foot_down_frames"] = 0
            return

        if test["status"] == "running":
            dur_frames = frame_count - test["start_frame"]
            dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
            # 检测脚落地：双踝高度差小于阈值持续 5 帧
            if not foot_lifted:
                test["foot_down_frames"] = test.get("foot_down_frames", 0) + 1
                if test["foot_down_frames"] >= 5:
                    test["status"] = "done"
                    test["completed"] = True
                    test["data"] = {"duration": round(dur_seconds, 1)}
                    test["score"] = round(self.engine.score_balance(dur_seconds).score, 1)
            else:
                test["foot_down_frames"] = 0
            # 不强制结束 — 持续计时直到脚落地或视频结束

    def _eval_squat_video(self, state, angles, kps):
        test = state.current_test()
        knee = angles.get("left_knee") or angles.get("right_knee") or 180
        if test["status"] == "pending" or test["status"] == "ready":
            test["status"] = "running"
            test["knee_vals"] = []
            return

        if knee < 120:
            test["knee_vals"].append(knee)
            if knee < 90:
                test["status"] = "done"
                test["completed"] = True
                avg = sum(test["knee_vals"]) / len(test["knee_vals"])
                test["data"] = {"depth_angle": round(avg, 1)}
                test["score"] = round(self.engine.score_flexibility(avg, 0, 1.0).score, 1)

    def _eval_shoulder_video(self, state, angles, kps):
        """肩关节活动度：检测双手在背后相互靠近的距离"""
        test = state.current_test()
        if test["status"] == "pending" or test["status"] == "ready":
            test["status"] = "running"
            test["poses"] = 0
            test["dists"] = []
            return

        ls = kps[5][:2] if len(kps) > 5 else [0, 0]
        rs = kps[6][:2] if len(kps) > 6 else [0, 0]
        lw = kps[9][:2] if len(kps) > 9 else [0, 0]
        rw = kps[10][:2] if len(kps) > 10 else [0, 0]

        left_behind = lw[1] > ls[1] + 20 if lw[1] > 0 and ls[1] > 0 else False
        right_behind = rw[1] > rs[1] + 20 if rw[1] > 0 and rs[1] > 0 else False
        any_behind = left_behind or right_behind

        # 用肩宽作为参考尺，将像素转换为厘米
        shoulder_width_px = float(np.linalg.norm(np.array(ls[:2]) - np.array(rs[:2]))) if ls[0] > 0 and rs[0] > 0 else 200
        px_to_cm = 38.0 / max(shoulder_width_px, 1)

        if any_behind:
            test["poses"] += 1
            if lw[0] > 0 and lw[1] > 0 and rw[0] > 0 and rw[1] > 0:
                dist_px = float(np.linalg.norm(np.array(lw[:2]) - np.array(rw[:2])))
                dist_cm = round(dist_px * px_to_cm, 1)
            else:
                dist_cm = 60.0
            test["dists"].append(dist_cm)
            if test["poses"] >= 5:
                test["status"] = "done"
                test["completed"] = True
                best_dists = sorted(test["dists"])[:max(3, len(test["dists"]) // 3)]
                avg = sum(best_dists) / len(best_dists)
                test["data"] = {"hand_distance": round(avg, 1)}
                test["score"] = round(self.engine.score_upper_limb(avg).score, 1)

    def _eval_plank_video(self, state, angles, kps, frame_count=0, fps=30.0):
        test = state.current_test()
        ls = kps[5][1] if len(kps) > 5 and kps[5][1] > 0 else 0
        la = kps[15][1] if len(kps) > 15 and kps[15][1] > 0 else 0
        horiz = abs(ls - la) < 100 if ls > 0 and la > 0 else False

        if test["status"] == "pending" or test["status"] == "ready":
            if horiz:
                test["status"] = "running"
                test["start_frame"] = frame_count
            return

        if test["status"] == "running":
            dur_frames = frame_count - test.get("start_frame", 0)
            dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
            # 身体不再保持水平且已持续至少 1 秒 → 结束
            if not horiz and dur_seconds >= 1.0:
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration": round(dur_seconds, 1)}
                test["score"] = round(self.engine.score_core(dur_seconds).score, 1)
            # 不强制结束 — 持续计时直到姿势变形或视频结束

    def _eval_symmetry_video(self, state, angles, kps):
        test = state.current_test()
        kl = angles.get("left_knee", 180) or 180
        kr = angles.get("right_knee", 180) or 180

        if test["status"] == "pending" or test["status"] == "ready":
            test["status"] = "running_left"
            test["cl"] = []
            test["cr"] = []
            return

        if test["status"] == "running_left":
            if kl < 120:
                test["cl"].append(kl)
            if len(test["cl"]) >= 3:
                test["status"] = "running_right"
                test["left_score"] = max(0, 100 - abs(90 - sum(test["cl"]) / len(test["cl"])))
            return

        if test["status"] == "running_right":
            if kr < 120:
                test["cr"].append(kr)
            if len(test["cr"]) >= 3:
                test["right_score"] = max(0, 100 - abs(90 - sum(test["cr"]) / len(test["cr"])))
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {
                    "left_score": round(test["left_score"], 1),
                    "right_score": round(test["right_score"], 1),
                }
                test["score"] = round(self.engine.score_symmetry(test["left_score"], test["right_score"]).score, 1)

    def _build_result(self, state, user_id: int, best_keypoints_all: list) -> dict:
        tests_completed = [t for t in state.tests if t.get("completed")]
        tests_skipped = [t for t in state.tests if t.get("status") == "skipped"]

        score_map = {"balance": None, "flexibility": None, "upper_limb": None, "core": None, "symmetry": None}
        score_list = []
        for t in tests_completed:
            idx = t.get("idx", 0)
            sc = t.get("score", 0)
            dim_map = {0: "balance", 1: "flexibility", 2: "upper_limb", 3: "core", 4: "symmetry"}
            dim = dim_map.get(idx, "unknown")
            score_map[dim] = sc
            score_list.append({"dimension": dim, "label": dim, "score": sc})

        scores_only = [s["score"] for s in score_list if s["score"] is not None]
        overall = round(sum(scores_only) / len(scores_only), 1) if scores_only else 0

        if overall >= 70:
            risk = "low"
        elif overall >= 40:
            risk = "medium"
        else:
            risk = "high"

        record_id = None
        try:
            from backend.database import models as db_models
            record = db_models.FMSRecord(
                user_id=user_id,
                balance_score=score_map.get("balance"),
                flexibility_score=score_map.get("flexibility"),
                upper_limb_score=score_map.get("upper_limb"),
                core_score=score_map.get("core"),
                symmetry_score=score_map.get("symmetry"),
                overall_score=overall,
                risk_level=risk,
                test_date=datetime.utcnow(),
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            record_id = record.id
            logger.info("[VideoFMS] Saved record id=%s user=%s score=%s", record_id, user_id, overall)
        except Exception as e:
            import traceback
            logger.exception("[VideoFMS] DB save failed: %s", e)
            try:
                self.db.rollback()
            except:
                pass

        posture_report = {}
        if best_keypoints_all:
            try:
                from models.posture_analyzer import PostureAnalyzer
                analyzer = PostureAnalyzer()
                best_kps = max(best_keypoints_all, key=lambda k: sum(1 for p in k if p[1] > 0))
                measurements = analyzer.analyze_from_keypoints(best_kps)
                posture_report = analyzer.generate_report(measurements, score_list)
            except Exception as e:
                logger.warning("[VideoFMS] Posture analysis error: %s", e)

        return {
            "type": "fms_result",
            "overall_score": overall,
            "risk_level": risk,
            "record_id": record_id,
            "completed_count": len(tests_completed),
            "skipped_count": len(tests_skipped),
            "scores": score_list,
            "problem_tags": [],
            "posture_report": posture_report,
        }

    # ─── 单动作视频处理 ──────────────────────────────────
    async def process_single_test_video(self, video_path: str, test_index: int, user_id: int) -> dict:
        """处理单个 FMS 动作的视频，返回该动作的评分"""
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0:
            cap.release()
            raise Exception("视频文件为空")

        logger.info("[VideoFMS] Processing single test %s: %s frames, %.1f FPS", test_index, total_frames, fps)

        # 跳帧：仅时长型测试（平衡、平板支撑）跳帧到 ~2 FPS，其他全帧保证精度
        if test_index in (0, 3):
            frame_skip = max(1, int(fps / 2)) if fps > 0 else 1
        else:
            frame_skip = 1
        logger.info("[VideoFMS] Single test %s frame skip: %s (FPS=%.1f)", test_index, frame_skip, fps)

        yolo = self._get_yolo()
        frame_count = 0
        real_frame_count = 0
        best_keypoints = None

        # 骨架视频：边处理边生成（源帧率输出，时长一致）
        out_fps = fps  # 用源帧率保证时长正确
        render_skip = max(1, int(fps / 10))  # 每 N 帧渲染一次骨架，约10fps的骨架更新
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        out_w = min(orig_w, 960)
        out_h = int(orig_h * out_w / orig_w)
        processed_video_path = os.path.join(
            os.path.dirname(video_path),
            f"processed_{os.path.basename(video_path)}"
        )
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_out = cv2.VideoWriter(processed_video_path, fourcc, out_fps, (out_w, out_h))
        last_persons = []  # 保存最近的骨架数据，无骨架帧复用
        if not video_out.isOpened():
            logger.warning("[VideoFMS] VideoWriter failed, trying avc1 fallback")
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            video_out = cv2.VideoWriter(processed_video_path, fourcc, out_fps, (out_w, out_h))
        render_enabled = video_out.isOpened()
        logger.info("[VideoFMS] Rendering skeleton video: %s @ %.0ffps, render_skip=%s (opened=%s)", processed_video_path, out_fps, render_skip, render_enabled)

        test = {
            "idx": test_index,
            "status": "pending",
            "completed": False,
            "score": 0,
            "data": {},
        }

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # 跳帧：只对 YOLO 分析跳帧，但渲染输出每帧都写
            do_analyze = real_frame_count % frame_skip == 0

            if do_analyze:
                persons, _ = yolo.process_frame(frame)
                if persons:
                    last_persons = persons
            else:
                persons = last_persons if last_persons else []

            # 骨架视频渲染：每帧都输出，有骨架则画骨架
            if render_enabled:
                if persons:
                    vis_frame = yolo.draw_keypoints(frame, persons)
                else:
                    vis_frame = frame
                video_out.write(cv2.resize(vis_frame, (out_w, out_h)))

            if not do_analyze:
                real_frame_count += 1
                continue

            if not persons:
                frame_count += 1
                real_frame_count += 1
                continue

            person = persons[0]
            kps = np.array(person["keypoints"])
            bbox = person.get("bbox")
            if bbox and (best_keypoints is None or (bbox[3] - bbox[1]) > 100):
                best_keypoints = person["keypoints"]

            angles = self.angle_calc.compute_all_angles(kps)

            if test_index == 0:
                self._eval_balance_single(test, angles, kps, real_frame_count, fps)
            elif test_index == 1:
                self._eval_squat_single(test, angles, kps)
            elif test_index == 2:
                self._eval_shoulder_single(test, angles, kps)
            elif test_index == 3:
                self._eval_plank_single(test, angles, kps, real_frame_count, fps)
            elif test_index == 4:
                self._eval_symmetry_single(test, angles, kps)

            if test.get("completed") and not test.get("_rendering_done"):
                test["_rendering_done"] = True
                logger.info("[VideoFMS] Single test %s completed, score=%s (continuing render)", test_index, test.get('score'))
                # 不 break — 继续渲染完整视频

            frame_count += 1
            real_frame_count += 1
            if real_frame_count % (30 * frame_skip) == 0:
                logger.debug("[VideoFMS] Progress: %s/%s real frames", real_frame_count, total_frames)

        # 视频播放完毕，若测试仍在运行中则根据累计时间计分
        if not test.get("completed") and test.get("status", "").startswith("running"):
            if test_index == 0:
                dur_frames = real_frame_count - test.get("start_frame", 0)
                dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
                test["data"] = {"duration": round(dur_seconds, 1)}
                test["score"] = round(self.engine.score_balance(dur_seconds).score, 1)
                test["status"] = "done"
                test["completed"] = True
                logger.info("[VideoFMS] Balance test ended by video end, dur=%.1fs score=%s", dur_seconds, test["score"])
            elif test_index == 3:
                dur_frames = real_frame_count - test.get("start_frame", 0)
                dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
                test["data"] = {"duration": round(dur_seconds, 1)}
                test["score"] = round(self.engine.score_core(dur_seconds).score, 1)
                test["status"] = "done"
                test["completed"] = True
                logger.info("[VideoFMS] Plank test ended by video end, dur=%.1fs score=%s", dur_seconds, test["score"])
            elif test_index == 4:
                # 弓步蹲：用已收集的数据计分
                cl = test.get("cl", []); cr = test.get("cr", [])
                if not cl and not cr:
                    test["score"] = 0
                    test["data"] = {"left_score": 0, "right_score": 0, "warning": "未检测到有效的弓步蹲动作"}
                else:
                    ls = max(0, 100 - abs(90 - sum(cl)/len(cl))) if cl else 0
                    rs = max(0, 100 - abs(90 - sum(cr)/len(cr))) if cr else 0
                    test["left_score"] = ls; test["right_score"] = rs
                    test["data"] = {"left_score": round(ls, 1), "right_score": round(rs, 1)}
                    test["score"] = round(self.engine.score_symmetry(ls, rs).score, 1)
                test["status"] = "done"
                test["completed"] = True
                logger.info("[VideoFMS] Symmetry test ended by video end, L=%.1f R=%.1f score=%s", ls, rs, test["score"])
            elif test_index == 2:
                # 肩关节活动度：用已收集的距离数据计分
                dists = test.get("dists", [])
                if dists:
                    best_dists = sorted(dists)[:max(3, len(dists) // 3)]
                    avg = sum(best_dists) / len(best_dists)
                else:
                    avg = 50.0
                test["data"] = {"hand_distance": round(avg, 1)}
                test["score"] = round(self.engine.score_upper_limb(avg).score, 1)
                test["status"] = "done"
                test["completed"] = True
                logger.info("[VideoFMS] Shoulder test ended by video end, avg_dist=%.1fcm score=%s", avg, test["score"])

        cap.release()
        video_out.release()

        # 生成处理后视频的相对 URL
        # 验证文件确实有内容才返回URL
        processed_video_url = None
        if os.path.isfile(processed_video_path) and os.path.getsize(processed_video_path) > 1000:
            processed_filename = os.path.basename(processed_video_path)
            processed_video_url = f"/api/fms/processed-video/{processed_filename}"
        else:
            logger.warning("[VideoFMS] Processed video empty or missing: %s", processed_video_path)

        with _single_test_results_lock:
            _single_test_results_global[f"{user_id}_{test_index}"] = {
                "test_index": test_index,
                "score": test.get("score", 0),
                "data": test.get("data", {}),
                "completed": test.get("completed", False),
                "best_keypoints": best_keypoints,
            }

        dim_map = {0: "balance", 1: "flexibility", 2: "upper_limb", 3: "core", 4: "symmetry"}
        dim = dim_map.get(test_index, "unknown")

        return {
            "type": "single_test_result",
            "test_index": test_index,
            "dimension": dim,
            "score": test.get("score", 0),
            "data": test.get("data", {}),
            "completed": test.get("completed", False),
            "processed_video_url": processed_video_url,
        }

    # ─── 单测试评估函数 ────────────────────────────────
    def _eval_balance_single(self, test, angles, kps, frame_count, fps):
        left_ankle = kps[15][:2] if len(kps) > 15 else [0, 0]
        right_ankle = kps[16][:2] if len(kps) > 16 else [0, 0]
        ankle_diff = abs(left_ankle[1] - right_ankle[1])
        foot_lifted = ankle_diff > 30

        if test["status"] == "pending" or test["status"] == "ready":
            if foot_lifted:
                test["status"] = "running"
                test["start_frame"] = frame_count
                test["foot_down_frames"] = 0
            return

        if test["status"] == "running":
            dur_frames = frame_count - test["start_frame"]
            dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
            # 检测脚落地：双踝高度差小于阈值持续 5 帧
            if not foot_lifted:
                test["foot_down_frames"] = test.get("foot_down_frames", 0) + 1
                if test["foot_down_frames"] >= 5:
                    test["status"] = "done"
                    test["completed"] = True
                    test["data"] = {"duration": round(dur_seconds, 1)}
                    test["score"] = round(self.engine.score_balance(dur_seconds).score, 1)
            else:
                test["foot_down_frames"] = 0
            # 不强制结束 — 持续计时直到脚落地或视频结束

    def _eval_squat_single(self, test, angles, kps):
        knee = angles.get("left_knee") or angles.get("right_knee") or 180
        if test["status"] == "pending" or test["status"] == "ready":
            test["status"] = "running"
            test["knee_vals"] = []
            return

        if knee < 120:
            test["knee_vals"].append(knee)
            if knee < 90:
                test["status"] = "done"
                test["completed"] = True
                avg = sum(test["knee_vals"]) / len(test["knee_vals"])
                test["data"] = {"depth_angle": round(avg, 1)}
                test["score"] = round(self.engine.score_flexibility(avg, 0, 1.0).score, 1)

    def _eval_shoulder_single(self, test, angles, kps):
        """肩关节活动度：检测双手相互靠近的距离（至少一只手在背后）"""
        if test["status"] == "pending" or test["status"] == "ready":
            test["status"] = "running"
            test["poses"] = 0
            test["dists"] = []
            return

        # COCO关键点索引: 5=左肩, 6=右肩, 9=左手腕, 10=右手腕
        ls = kps[5][:2] if len(kps) > 5 else [0, 0]
        rs = kps[6][:2] if len(kps) > 6 else [0, 0]
        lw = kps[9][:2] if len(kps) > 9 else [0, 0]
        rw = kps[10][:2] if len(kps) > 10 else [0, 0]

        # 至少一只手在背后（手腕Y > 同侧肩Y + 20）
        left_behind = lw[1] > ls[1] + 20 if lw[1] > 0 and ls[1] > 0 else False
        right_behind = rw[1] > rs[1] + 20 if rw[1] > 0 and rs[1] > 0 else False
        any_behind = left_behind or right_behind

        # 用肩宽作为参考尺，将像素距离转换为近似厘米
        shoulder_width_px = float(np.linalg.norm(np.array(ls[:2]) - np.array(rs[:2]))) if ls[0] > 0 and rs[0] > 0 else 200
        px_to_cm = 38.0 / max(shoulder_width_px, 1)

        if any_behind:
            test["poses"] += 1
            if lw[0] > 0 and lw[1] > 0 and rw[0] > 0 and rw[1] > 0:
                dist_px = float(np.linalg.norm(np.array(lw[:2]) - np.array(rw[:2])))
                dist_cm = round(dist_px * px_to_cm, 1)
            else:
                dist_cm = 60.0
            test["dists"].append(dist_cm)
            if test["poses"] >= 5:
                test["status"] = "done"
                test["completed"] = True
                # 取距离最小的几次（最接近的时刻）
                best_dists = sorted(test["dists"])[:max(3, len(test["dists"]) // 3)]
                avg = sum(best_dists) / len(best_dists)
                test["data"] = {"hand_distance": round(avg, 1)}
                test["score"] = round(self.engine.score_upper_limb(avg).score, 1)

    def _eval_plank_single(self, test, angles, kps, frame_count=0, fps=30.0):
        ls = kps[5][1] if len(kps) > 5 and kps[5][1] > 0 else 0
        la = kps[15][1] if len(kps) > 15 and kps[15][1] > 0 else 0
        horiz = abs(ls - la) < 100 if ls > 0 and la > 0 else False

        if test["status"] == "pending" or test["status"] == "ready":
            if horiz:
                test["status"] = "running"
                test["start_frame"] = frame_count
            return

        if test["status"] == "running":
            dur_frames = frame_count - test.get("start_frame", 0)
            dur_seconds = dur_frames / fps if fps > 0 else dur_frames / 30.0
            # 身体不再保持水平且已持续至少 1 秒 → 结束
            if not horiz and dur_seconds >= 1.0:
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration": round(dur_seconds, 1)}
                test["score"] = round(self.engine.score_core(dur_seconds).score, 1)
            # 不强制结束 — 持续计时直到姿势变形或视频结束

    def _eval_symmetry_single(self, test, angles, kps):
        kl = angles.get("left_knee", 180) or 180
        kr = angles.get("right_knee", 180) or 180

        if test["status"] == "pending" or test["status"] == "ready":
            test["status"] = "running_left"
            test["cl"] = []
            test["cr"] = []
            return

        if test["status"] == "running_left":
            if kl < 120:
                test["cl"].append(kl)
            if len(test["cl"]) >= 3:
                test["status"] = "running_right"
                test["left_score"] = max(0, 100 - abs(90 - sum(test["cl"]) / len(test["cl"])))
            return

        if test["status"] == "running_right":
            if kr < 120:
                test["cr"].append(kr)
            if len(test["cr"]) >= 3:
                test["right_score"] = max(0, 100 - abs(90 - sum(test["cr"]) / len(test["cr"])))
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {
                    "left_score": round(test["left_score"], 1),
                    "right_score": round(test["right_score"], 1),
                }
                test["score"] = round(self.engine.score_symmetry(test["left_score"], test["right_score"]).score, 1)

    async def combine_results(self, user_id: int) -> dict:
        """合并所有已上传的单个动作评分，生成最终 FMS 报告"""
        # 从全局存储中获取该用户的所有测试结果
        dim_map = {0: "balance", 1: "flexibility", 2: "upper_limb", 3: "core", 4: "symmetry"}
        dim_labels = {0: "平衡控制", 1: "下肢柔韧性", 2: "肩关节活动度", 3: "核心稳定性", 4: "左右对称性"}
        score_map = {"balance": None, "flexibility": None, "upper_limb": None, "core": None, "symmetry": None}
        score_list = []
        best_keypoints_all = []

        for idx in range(5):
            key = f"{user_id}_{idx}"
            with _single_test_results_lock:
                result = _single_test_results_global.get(key)
            if result and result.get("completed"):
                dim = dim_map.get(idx, "unknown")
                sc = result.get("score", 0)
                score_map[dim] = sc
                score_list.append({"dimension": dim, "label": dim_labels.get(idx, dim), "score": sc})
                if result.get("best_keypoints"):
                    best_keypoints_all.append(result["best_keypoints"])

        scores_only = [s["score"] for s in score_list if s["score"] is not None]
        overall = round(sum(scores_only) / len(scores_only), 1) if scores_only else 0

        if overall >= 70:
            risk = "low"
        elif overall >= 40:
            risk = "medium"
        else:
            risk = "high"

        # 生成问题标签
        problem_tags = []
        for s in score_list:
            if s["score"] < 40:
                problem_tags.append({
                    "name": s["label"],
                    "description": f"{s['label']}评分较低（{s['score']}分），建议加强相关训练",
                    "severity": "high",
                })
            elif s["score"] < 60:
                problem_tags.append({
                    "name": s["label"],
                    "description": f"{s['label']}评分偏低（{s['score']}分），需要针对性改善",
                    "severity": "medium",
                })

        # 生成建议
        suggestions = []
        if score_map.get("balance") is not None and score_map["balance"] < 60:
            suggestions.append("平衡能力较弱，建议增加单腿站立、闭眼站立等平衡训练")
        if score_map.get("flexibility") is not None and score_map["flexibility"] < 60:
            suggestions.append("下肢柔韧性不足，建议增加深蹲、弓步拉伸等柔韧性训练")
        if score_map.get("upper_limb") is not None and score_map["upper_limb"] < 60:
            suggestions.append("肩关节活动度受限，建议增加肩部拉伸和活动度训练")
        if score_map.get("core") is not None and score_map["core"] < 60:
            suggestions.append("核心稳定性不足，建议增加平板支撑、桥式等核心训练")
        if score_map.get("symmetry") is not None and score_map["symmetry"] < 60:
            suggestions.append("左右对称性较差，建议增加单侧训练以改善身体平衡")
        if not suggestions:
            suggestions.append("各项能力良好，继续保持规律训练")

        # 保存到数据库
        record_id = None
        try:
            from backend.database import models as db_models
            record = db_models.FMSRecord(
                user_id=user_id,
                balance_score=score_map.get("balance"),
                flexibility_score=score_map.get("flexibility"),
                upper_limb_score=score_map.get("upper_limb"),
                core_score=score_map.get("core"),
                symmetry_score=score_map.get("symmetry"),
                overall_score=overall,
                risk_level=risk,
                test_date=datetime.utcnow(),
            )
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
            record_id = record.id
            logger.info("[VideoFMS] Combined result saved record id=%s user=%s score=%s", record_id, user_id, overall)
        except Exception as e:
            import traceback
            logger.exception("[VideoFMS] DB save failed: %s", e)
            try:
                self.db.rollback()
            except:
                pass

        # 清理临时存储
        with _single_test_results_lock:
            for idx in range(5):
                key = f"{user_id}_{idx}"
                _single_test_results_global.pop(key, None)

        # 构建雷达图数据
        radar_data = {
            "dimensions": score_list,
            "chart_data": {
                "labels": [s["label"] for s in score_list],
                "values": [s["score"] for s in score_list],
            },
            "suggestions": suggestions,
        }

        return {
            "type": "fms_result",
            "overall_score": overall,
            "risk_level": risk,
            "record_id": record_id,
            "completed_count": len(score_list),
            "skipped_count": 5 - len(score_list),
            "scores": score_list,
            "radar_data": radar_data,
            "problem_tags": problem_tags,
            "posture_report": {},
        }

