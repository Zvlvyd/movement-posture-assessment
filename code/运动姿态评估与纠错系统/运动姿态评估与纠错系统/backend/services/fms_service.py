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


class RealtimeFMSService:
    def __init__(self, db: Session):
        self.db = db
        self.angle_calc = AngleCalculator()
        self.engine = FMSScoringEngine()
        self.yolo = None

    def _get_yolo(self):
        if self.yolo is None:
            from models.yolo_pose_engine import YOLOPoseEngine
            from backend.config import settings
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
        lw = kps[9][:2] if len(kps)>9 else [0,0]
        rw = kps[10][:2] if len(kps)>10 else [0,0]
        ls = kps[5][:2] if len(kps)>5 else [0,0]
        behind = lw[1] < ls[1] + 50 if lw[1]>0 and ls[1]>0 else False
        if behind:
            t["poses"] += 1; dist = abs(rw[0]-lw[0]) if rw[0]>0 and lw[0]>0 else 100
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
            {"idx":0,"name":"test0","instruction":"do test 0","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":1,"name":"test1","instruction":"do test 1","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":2,"name":"test2","instruction":"do test 2","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":3,"name":"test3","instruction":"do test 3","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
            {"idx":4,"name":"test4","instruction":"do test 4","status":"pending","start_time":0,"data":None,"score":0,"completed":False},
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
