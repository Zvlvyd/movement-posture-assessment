from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Optional, List
from backend.database import models
from models.fms.scoring import FMSScoringEngine
from models.fms.radar_report import RadarReport
from models.fms.problem_tagger import ProblemTagger
from backend.schemas.business import FMSSubmitRequest, FMSResultResponse

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
        return FMSResultResponse.model_validate(record)

import json, math, time
from typing import Dict, List, Optional, Any
from fastapi import WebSocket
from sqlalchemy.orm import Session
from datetime import datetime
import numpy as np

from models.angle_calculator import AngleCalculator

# 全局存储：跨请求共享单动作视频处理结果
# key: "{user_id}_{test_index}", value: dict with score, data, completed, best_keypoints
_single_test_results_global: Dict[str, dict] = {}


class RealtimeFMSService:
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
                    t = state.tests[0]
                    t["status"] = "ready"
                    await ws.send_json({"type":"test_ready","test":0,"name":t["name"],"instruction":t["instruction"],"total_tests":5})
                elif mt == "skip_test":
                    test = state.current_test()
                    if test:
                        test["status"] = "skipped"
                        test["completed"] = True
                        test["score"] = 0
                        test["data"] = {"skipped": True}
                    idx = state.advance_to_next()
                    if idx >= 0:
                        t = state.current_test()
                        t["status"] = "ready"
                        await ws.send_json({"type":"test_ready","test":idx,"name":t["name"],"instruction":t["instruction"],"total_tests":5})
                    else:
                        await self._send_final_result(ws, state, user_id)
                elif mt == "frame":
                    test = state.current_test()
                    if not test or test["status"] == "done" or test["status"] == "skipped":
                        continue
                    b64 = msg.get("image","")
                    if not b64:
                        continue
                    try:
                        yolo = self._get_yolo()
                        persons, _ = yolo.process_base64_frame(b64)
                        keypoints_list = []
                        for p in persons:
                            kps = p.get("keypoints", [])
                            confs = p.get("confidences", [1.0]*len(kps))
                            keypoints_list.append({"keypoints": kps, "confidences": confs, "bbox": p.get("bbox")})
                        
                        eval_res = {"type":"frame_result","test_idx":state.current_test_idx,"keypoints": keypoints_list}
                        
                        if not persons:
                            eval_res["fms_status"] = "no_person"
                            await ws.send_json(eval_res)
                            continue
                        
                        person = persons[0]
                        kps = np.array(person["keypoints"])
                        # Store best keypoints for posture analysis (tallest person)
                        bbox = person.get("bbox")
                        if bbox and (state.best_keypoints is None or (bbox[3] - bbox[1]) > 100):
                            state.best_keypoints = person["keypoints"]
                        angles = self.angle_calc.compute_all_angles(kps)
                        test_idx = state.current_test_idx
                        
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
                        if eval_res.get("fms_status") == "completed":
                            eval_res["wait_advance"] = True
                        
                        await ws.send_json(eval_res)
                    except Exception as e:
                        import traceback
                        print(f"FMS frame error: {e}")
                        traceback.print_exc()
                        try:
                            await ws.send_json({"type":"frame_result","error":str(e)})
                        except:
                            pass
                elif mt == "next_test":
                    print(f"[FMS] next_test received, idx={state.current_test_idx}")
                    idx = state.advance_to_next()
                    if idx >= 0:
                        t = state.current_test()
                        t["status"] = "ready"
                        await ws.send_json({"type":"test_ready","test":idx,"name":t["name"],"instruction":t["instruction"],"total_tests":5})
                    else:
                        await self._send_final_result(ws, state, user_id)
                elif mt == "finish":
                    print(f"[FMS] finish received")
                    await self._send_final_result(ws, state, user_id)
        except Exception as e:
            print(f"FMS WS error: {e}")
            try: await ws.close()
            except: pass

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
                label_map = {0: "balance", 1: "flexibility", 2: "upper_limb", 3: "core", 4: "symmetry"}
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
                print(f"[FMS] Saved record id={record_id} user={user_id} score={overall}")
            except Exception as e:
                import traceback
                print(f"[FMS] DB save failed: {e}")
                traceback.print_exc()
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
                    print(f"[FMS] Posture: {len(posture_report.get('problems',[]))} problems")
                except Exception as e:
                    print(f"[FMS] Posture analysis error: {e}")

            result = {
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
            await ws.send_json(result)
        except Exception as e:
            import traceback
            print(f"[FMS] final result error: {e}")
            traceback.print_exc()
            try:
                await ws.send_json({"type":"fms_result","overall_score":0,"risk_level":"unknown","scores":[],"error":str(e)})
            except:
                pass

    def _eval_balance(self, state, angles, kps):
        t = state.current_test()
        if t["status"] == "ready":
            t["status"] = "running"
            t["start_time"] = time.time()
            return {"fms_status":"started"}
        dur = time.time() - t["start_time"]
        if dur > 1:
            t["status"] = "done"; t["completed"] = True
            t["data"] = {"duration": round(dur,1)}
            t["score"] = round(self.engine.score_balance(dur).score,1)
            return {"fms_status":"completed","duration":round(dur,1),"score":t["score"]}
        return {"fms_status":"running","duration":round(dur,1)}

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
        # COCO关键点索引: 5=左肩, 6=右肩, 7=左肘, 8=右肘, 9=左手腕, 10=右手腕
        ls = kps[5][:2] if len(kps)>5 else [0,0]
        rs = kps[6][:2] if len(kps)>6 else [0,0]
        le = kps[7][:2] if len(kps)>7 else [0,0]
        re = kps[8][:2] if len(kps)>8 else [0,0]
        lw = kps[9][:2] if len(kps)>9 else [0,0]
        rw = kps[10][:2] if len(kps)>10 else [0,0]

        # 检测"手在背后"：手腕在肩膀下方（Y坐标更大），且手肘弯曲
        # 图像坐标系Y向下增大，所以手腕Y > 肩膀Y 表示手在下方（背后）
        left_behind = lw[1] > ls[1] + 30 if lw[1]>0 and ls[1]>0 else False
        right_behind = rw[1] > rs[1] + 30 if rw[1]>0 and rs[1]>0 else False

        # 检测是否有一只手在背后（上手下背式）
        behind = left_behind or right_behind

        if behind:
            t["poses"] += 1
            # 计算双手之间的垂直距离（上下距离）
            # 如果左手在上（Y较小），右手在下（Y较大）
            if lw[1] > 0 and rw[1] > 0:
                vert_dist = abs(lw[1] - rw[1])  # 垂直距离
                horiz_dist = abs(lw[0] - rw[0])  # 水平距离
                # 综合距离 = 垂直距离为主，水平距离为辅
                dist = vert_dist * 0.7 + horiz_dist * 0.3
            else:
                dist = 100
            t["dists"].append(dist)
            if t["poses"] >= 5:
                t["status"] = "done"; t["completed"] = True
                avg = sum(t["dists"])/len(t["dists"])
                t["data"] = {"hand_distance": round(avg,1)}
                t["score"] = round(self.engine.score_upper_limb(avg).score,1)
                return {"fms_status":"completed","hand_distance":round(avg,1),"score":t["score"]}
            return {"fms_status":"running","hand_distance":round(dist,1)}
        return {"fms_status":"running"}

    def _eval_plank(self, state, angles, kps):
        t = state.current_test()
        ls = kps[5][1] if len(kps)>5 and kps[5][1]>0 else 0
        la = kps[15][1] if len(kps)>15 and kps[15][1]>0 else 0
        horiz = abs(ls-la) < 100 if ls>0 and la>0 else False
        if t["status"] == "ready":
            if horiz:
                t["status"] = "running"; t["start_time"] = time.time()
                return {"fms_status":"started"}
            return {"fms_status":"ready"}
        dur = time.time() - t["start_time"]
        if not horiz and dur > 1:
            t["status"] = "done"; t["completed"] = True
            t["data"] = {"duration": round(dur,1)}
            t["score"] = round(self.engine.score_core(dur).score,1)
            return {"fms_status":"completed","duration":round(dur,1),"score":t["score"]}
        return {"fms_status":"running","duration":round(dur,1)}

    def _eval_symmetry(self, state, angles, kps):
        t = state.current_test()
        kl = angles.get("left_knee",180) or 180
        kr = angles.get("right_knee",180) or 180
        if t["status"] == "ready":
            t["status"] = "running_left"; t["cl"]=[]; t["cr"]=[]
            return {"fms_status":"started","side":"left"}
        if t["status"] == "running_left":
            if kl < 120: t["cl"].append(kl)
            if len(t["cl"]) >= 3:
                t["status"] = "running_right"
                t["left_score"] = max(0, 100 - abs(90 - sum(t["cl"])/len(t["cl"])))
                return {"fms_status":"step_complete","side":"left","score":round(t["left_score"],1)}
            return {"fms_status":"running","side":"left"}
        if t["status"] == "running_right":
            if kr < 120: t["cr"].append(kr)
            if len(t["cr"]) >= 3:
                t["right_score"] = max(0, 100 - abs(90 - sum(t["cr"])/len(t["cr"])))
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
            {"idx":3,"name":"平板支撑","instruction":"俯卧，用前臂和脚尖支撑身体，保持成一条直线（坚持越久分数越高，满分120秒）","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
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

        print(f"[VideoFMS] Processing video: {total_frames} frames, {fps:.1f} FPS")

        state = FMSState()
        yolo = self._get_yolo()
        frame_count = 0
        best_keypoints_all = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            persons, _ = yolo.process_frame(frame)
            if not persons:
                frame_count += 1
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
                self._eval_balance_video(state, angles, kps, frame_count, fps)
            elif test_idx == 1:
                self._eval_squat_video(state, angles, kps)
            elif test_idx == 2:
                self._eval_shoulder_video(state, angles, kps)
            elif test_idx == 3:
                self._eval_plank_video(state, angles, kps)
            elif test_idx == 4:
                self._eval_symmetry_video(state, angles, kps)

            if test.get("completed"):
                print(f"[VideoFMS] Test {test_idx} completed, score={test.get('score')}")
                next_idx = state.advance_to_next()
                if next_idx < 0:
                    break

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[VideoFMS] Progress: {frame_count}/{total_frames} frames")

        cap.release()
        print(f"[VideoFMS] Video processing done, processed {frame_count} frames")

        return self._build_result(state, user_id, best_keypoints_all)

    def _eval_balance_video(self, state, angles, kps, frame_count, fps):
        test = state.current_test()
        if test["status"] == "pending" or test["status"] == "ready":
            left_ankle = kps[15][:2] if len(kps) > 15 else [0, 0]
            right_ankle = kps[16][:2] if len(kps) > 16 else [0, 0]
            if abs(left_ankle[1] - right_ankle[1]) > 30:
                test["status"] = "running"
                test["start_frame"] = frame_count
            return

        if test["status"] == "running":
            dur_frames = frame_count - test["start_frame"]
            dur_seconds = dur_frames / fps
            if dur_seconds > 1:
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration": round(dur_seconds, 1)}
                test["score"] = round(self.engine.score_balance(dur_seconds).score, 1)

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
        """肩关节活动度：检测双手背后距离"""
        test = state.current_test()
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

        # 检测"手在背后"：手腕在肩膀下方（Y坐标更大）
        # 图像坐标系Y向下增大，所以手腕Y > 肩膀Y 表示手在下方（背后）
        left_behind = lw[1] > ls[1] + 30 if lw[1] > 0 and ls[1] > 0 else False
        right_behind = rw[1] > rs[1] + 30 if rw[1] > 0 and rs[1] > 0 else False
        behind = left_behind or right_behind

        if behind:
            test["poses"] += 1
            # 计算双手之间的综合距离（垂直距离为主）
            if lw[1] > 0 and rw[1] > 0:
                vert_dist = abs(lw[1] - rw[1])
                horiz_dist = abs(lw[0] - rw[0])
                dist = vert_dist * 0.7 + horiz_dist * 0.3
            else:
                dist = 100
            test["dists"].append(dist)
            if test["poses"] >= 5:
                test["status"] = "done"
                test["completed"] = True
                avg = sum(test["dists"]) / len(test["dists"])
                test["data"] = {"hand_distance": round(avg, 1)}
                test["score"] = round(self.engine.score_upper_limb(avg).score, 1)

    def _eval_plank_video(self, state, angles, kps):
        test = state.current_test()
        ls = kps[5][1] if len(kps) > 5 and kps[5][1] > 0 else 0
        la = kps[15][1] if len(kps) > 15 and kps[15][1] > 0 else 0
        horiz = abs(ls - la) < 100 if ls > 0 and la > 0 else False

        if test["status"] == "pending" or test["status"] == "ready":
            if horiz:
                test["status"] = "running"
                test["start_frame"] = 0
                test["frame_count"] = 0
            return

        if test["status"] == "running":
            test["frame_count"] = test.get("frame_count", 0) + 1
            if not horiz and test["frame_count"] > 30:
                dur = test["frame_count"] / 30
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration": round(dur, 1)}
                test["score"] = round(self.engine.score_core(dur).score, 1)

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
            print(f"[VideoFMS] Saved record id={record_id} user={user_id} score={overall}")
        except Exception as e:
            import traceback
            print(f"[VideoFMS] DB save failed: {e}")
            traceback.print_exc()
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
                print(f"[VideoFMS] Posture analysis error: {e}")

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

        print(f"[VideoFMS] Processing single test {test_index}: {total_frames} frames, {fps:.1f} FPS")

        yolo = self._get_yolo()
        frame_count = 0
        best_keypoints = None

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

            persons, _ = yolo.process_frame(frame)
            if not persons:
                frame_count += 1
                continue

            person = persons[0]
            kps = np.array(person["keypoints"])
            bbox = person.get("bbox")
            if bbox and (best_keypoints is None or (bbox[3] - bbox[1]) > 100):
                best_keypoints = person["keypoints"]

            angles = self.angle_calc.compute_all_angles(kps)

            if test_index == 0:
                self._eval_balance_single(test, angles, kps, frame_count, fps)
            elif test_index == 1:
                self._eval_squat_single(test, angles, kps)
            elif test_index == 2:
                self._eval_shoulder_single(test, angles, kps)
            elif test_index == 3:
                self._eval_plank_single(test, angles, kps)
            elif test_index == 4:
                self._eval_symmetry_single(test, angles, kps)

            if test.get("completed"):
                print(f"[VideoFMS] Single test {test_index} completed, score={test.get('score')}")
                break

            frame_count += 1
            if frame_count % 30 == 0:
                print(f"[VideoFMS] Progress: {frame_count}/{total_frames} frames")

        cap.release()

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
        }

    # ─── 单测试评估函数 ────────────────────────────────
    def _eval_balance_single(self, test, angles, kps, frame_count, fps):
        if test["status"] == "pending" or test["status"] == "ready":
            left_ankle = kps[15][:2] if len(kps) > 15 else [0, 0]
            right_ankle = kps[16][:2] if len(kps) > 16 else [0, 0]
            if abs(left_ankle[1] - right_ankle[1]) > 30:
                test["status"] = "running"
                test["start_frame"] = frame_count
            return

        if test["status"] == "running":
            dur_frames = frame_count - test["start_frame"]
            dur_seconds = dur_frames / fps
            if dur_seconds > 1:
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration": round(dur_seconds, 1)}
                test["score"] = round(self.engine.score_balance(dur_seconds).score, 1)

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
        """肩关节活动度"""
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

        # 检测"手在背后"：手腕在肩膀下方（Y坐标更大）
        # 图像坐标系Y向下增大，所以手腕Y > 肩膀Y 表示手在下方（背后）
        left_behind = lw[1] > ls[1] + 30 if lw[1] > 0 and ls[1] > 0 else False
        right_behind = rw[1] > rs[1] + 30 if rw[1] > 0 and rs[1] > 0 else False
        behind = left_behind or right_behind

        if behind:
            test["poses"] += 1
            # 计算双手之间的综合距离（垂直距离为主）
            if lw[1] > 0 and rw[1] > 0:
                vert_dist = abs(lw[1] - rw[1])
                horiz_dist = abs(lw[0] - rw[0])
                dist = vert_dist * 0.7 + horiz_dist * 0.3
            else:
                dist = 100
            test["dists"].append(dist)
            if test["poses"] >= 5:
                test["status"] = "done"
                test["completed"] = True
                avg = sum(test["dists"]) / len(test["dists"])
                test["data"] = {"hand_distance": round(avg, 1)}
                test["score"] = round(self.engine.score_upper_limb(avg).score, 1)

    def _eval_plank_single(self, test, angles, kps):
        ls = kps[5][1] if len(kps) > 5 and kps[5][1] > 0 else 0
        la = kps[15][1] if len(kps) > 15 and kps[15][1] > 0 else 0
        horiz = abs(ls - la) < 100 if ls > 0 and la > 0 else False

        if test["status"] == "pending" or test["status"] == "ready":
            if horiz:
                test["status"] = "running"
                test["start_frame"] = 0
                test["frame_count"] = 0
            return

        if test["status"] == "running":
            test["frame_count"] = test.get("frame_count", 0) + 1
            if not horiz and test["frame_count"] > 30:
                dur = test["frame_count"] / 30
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration": round(dur, 1)}
                test["score"] = round(self.engine.score_core(dur).score, 1)

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
            print(f"[VideoFMS] Combined result saved record id={record_id} user={user_id} score={overall}")
        except Exception as e:
            import traceback
            print(f"[VideoFMS] DB save failed: {e}")
            traceback.print_exc()
            try:
                self.db.rollback()
            except:
                pass

        # 清理临时存储
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

