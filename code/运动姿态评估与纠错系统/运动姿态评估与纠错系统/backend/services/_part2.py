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
        await ws.accept()
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
                elif mt == "frame":
                    test = state.current_test()
                    if not test or test["status"] == "done":
                        continue
                    b64 = msg.get("image","")
                    if not b64:
                        continue
                    yolo = self._get_yolo()
                    persons, _ = yolo.process_base64_frame(b64)
                    eval_res = {"type":"frame_result","test_idx":state.current_test_idx}
                    if not persons:
                        eval_res["status"] = "no_person"
                        await ws.send_json(eval_res)
                        continue
                    kps = np.array(persons[0]["keypoints"], dtype=np.float32)
                    angles = self.angle_calc.compute_all_angles(kps)
                    state.last_angles = angles
                    state.frame_count += 1
                    eval_res["angles"] = {k:round(v,1) for k,v in angles.items() if v is not None}
                    eval_res["test_name"] = test["name"]
                    if state.current_test_idx == 0:
                        r = self._eval_balance(state, angles, kps)
                    elif state.current_test_idx == 1:
                        r = self._eval_flexibility(state, angles, kps)
                    elif state.current_test_idx == 2:
                        r = self._eval_upper_limb(state, angles, kps)
                    elif state.current_test_idx == 3:
                        r = self._eval_core(state, angles, kps)
                    elif state.current_test_idx == 4:
                        r = self._eval_symmetry(state, angles, kps)
                    else:
                        r = {}
                    eval_res.update(r)
                    if test.get("completed"):
                        eval_res["test_completed"] = True
                        eval_res["test_score"] = test.get("score",0)
                    await ws.send_json(eval_res)
                elif mt == "next_test":
                    if state.current_test_idx < 4:
                        state.current_test_idx += 1
                        t = state.tests[state.current_test_idx]
                        t["status"] = "ready"
                        await ws.send_json({"type":"test_ready","test":state.current_test_idx,"name":t["name"],"instruction":t["instruction"],"total_tests":5})
                    else:
                        await ws.send_json({"type":"all_tests_complete"})
                elif mt == "finish":
                    scores = []
                    for t in state.tests:
                        d = t.get("data",{})
                        if t["idx"] == 0:
                            scores.append(self.engine.score_balance(d.get("duration",0)))
                        elif t["idx"] == 1:
                            scores.append(self.engine.score_flexibility(d.get("depth_angle",90),d.get("trunk_tilt",20),d.get("arm_maintained",0.8)))
                        elif t["idx"] == 2:
                            scores.append(self.engine.score_upper_limb(d.get("hand_distance",20)))
                        elif t["idx"] == 3:
                            scores.append(self.engine.score_core(d.get("duration",0)))
                        elif t["idx"] == 4:
                            scores.append(self.engine.score_symmetry(d.get("left_score",50),d.get("right_score",50)))
                    if scores:
                        overall = self.engine.compute_overall(scores)
                        risk = self.engine.get_risk_level(overall,scores)
                        radar = RadarReport.generate(scores,overall,risk)
                        tags = ProblemTagger.tag(scores)
                        sugs = self._generate_training_suggestions(scores,tags)
                        record = models.FMSRecord(user_id=user_id,balance_score=next((s.score for s in scores if s.dimension=="balance"),None),flexibility_score=next((s.score for s in scores if s.dimension=="flexibility"),None),upper_limb_score=next((s.score for s in scores if s.dimension=="upper_limb"),None),core_score=next((s.score for s in scores if s.dimension=="core"),None),symmetry_score=next((s.score for s in scores if s.dimension=="symmetry"),None),overall_score=overall,risk_level=risk)
                        self.db.add(record); self.db.commit(); self.db.refresh(record)
                        await ws.send_json({"type":"fms_result","record_id":record.id,"overall_score":overall,"risk_level":risk,"radar_data":radar,"problem_tags":tags,"training_suggestions":sugs,"scores":[{"dimension":s.dimension,"score":round(s.score,1),"label":s.label} for s in scores]})
                    break
        except Exception as e:
            import traceback; traceback.print_exc()
            try: await ws.send_json({"type":"error","message":str(e)})
            except: pass

    def _eval_balance(self, state, angles, kps):
        t = state.current_test(); trunk = angles.get("trunk_tilt",0) or 0
        if t["status"] == "ready":
            t["status"] = "running"; t["start_time"] = time.time(); t["prev_trunk"] = trunk
            return {"fms_status":"started","message":"请闭上双眼，抬起单腿"}
        if t["status"] == "running":
            dur = time.time() - t["start_time"]; delta = abs(trunk - t.get("prev_trunk",trunk)); t["prev_trunk"] = trunk
            if trunk > 50 or delta > 20:
                if dur > 1.5:
                    t["status"] = "done"; t["completed"] = True; t["data"] = {"duration":round(dur,1)}
                    t["score"] = round(self.engine.score_balance(dur).score,1)
                    return {"fms_status":"completed","duration":round(dur,1),"score":t["score"],"body_observation":f"balance held {dur:.1f}s, trunk tilt {trunk:.0f} deg"}
            return {"fms_status":"running","duration":round(dur,1)}
        return {}

    def _eval_flexibility(self, state, angles, kps):
        t = state.current_test()
        if t["status"] == "ready":
            t["status"] = "running"; t["frames"] = []
            return {"fms_status":"started","message":"双手举过头顶，下蹲至最低点保持"}
        if t["status"] == "running":
            d = min(angles.get("left_knee",180) or 180, angles.get("right_knee",180) or 180)
            tr = angles.get("trunk_tilt",0) or 0
            t["frames"].append({"d":d,"tr":tr})
            if len(t["frames"]) >= 20:
                best = min(t["frames"], key=lambda x: x["d"])
                t["status"] = "done"; t["completed"] = True
                t["data"] = {"depth_angle":round(best["d"],1),"trunk_tilt":round(best["tr"],1),"arm_maintained":0.9 if best["tr"]<30 else 0.7}
                s = self.engine.score_flexibility(best["d"],best["tr"],0.85).score
                t["score"] = round(s,1)
                return {"fms_status":"completed","depth_angle":round(best["d"],1),"trunk_tilt":round(best["tr"],1),"score":t["score"],"body_observation":f"squat depth {best['d']:.0f} deg"}
            return {"fms_status":"running","depth_angle":round(d,1),"trunk_tilt":round(tr,1)}
        return {}

    def _eval_upper_limb(self, state, angles, kps):
        t = state.current_test()
        if t["status"] == "ready":
            t["status"] = "running"; t["frames"] = []
            return {"fms_status":"started","message":"一手从肩上、一手从腰后向背后靠拢"}
        if t["status"] == "running":
            ls = angles.get("left_shoulder",90) or 90; rs = angles.get("right_shoulder",90) or 90
            t["frames"].append({"ls":ls,"rs":rs})
            if len(t["frames"]) >= 10:
                avg_ls = sum(f["ls"] for f in t["frames"])/len(t["frames"])
                avg_rs = sum(f["rs"] for f in t["frames"])/len(t["frames"])
                hd = max(0, min(50, abs(avg_ls-avg_rs)*0.6))
                t["status"] = "done"; t["completed"] = True; t["data"] = {"hand_distance":round(hd,1)}
                t["score"] = round(self.engine.score_upper_limb(hd).score,1)
                return {"fms_status":"completed","hand_distance":round(hd,1),"score":t["score"],"body_observation":f"estimated hand distance {hd:.0f} cm"}
            return {"fms_status":"running"}
        return {}

    def _eval_core(self, state, angles, kps):
        t = state.current_test(); trunk = angles.get("trunk_tilt",0) or 0; hip = angles.get("left_hip",180) or 180
        if t["status"] == "ready":
            t["status"] = "running"; t["start_time"] = time.time()
            return {"fms_status":"started","message":"保持平板支撑姿势"}
        if t["status"] == "running":
            dur = time.time() - t["start_time"]
            if dur >= 60:
                t["status"]="done"; t["completed"]=True; t["data"]={"duration":60}; t["score"]=100
                return {"fms_status":"completed","duration":60,"score":100,"body_observation":"core endurance excellent"}
            if abs(180-hip)>25 or abs(trunk)>20:
                cd = max(3,round(dur-1,1))
                t["status"]="done"; t["completed"]=True; t["data"]={"duration":cd}
                t["score"]=round(self.engine.score_core(cd).score,1)
                return {"fms_status":"completed","duration":cd,"score":t["score"],"body_observation":f"plank broke at {cd}s"}
            return {"fms_status":"running","duration":round(dur,1)}
        return {}

    def _eval_symmetry(self, state, angles, kps):
        t = state.current_test(); kl = angles.get("left_knee",180) or 180; kr = angles.get("right_knee",180) or 180
        if t["status"] == "ready":
            t["status"] = "running_left"; t["cl"]=[]; t["cr"]=[]
            return {"fms_status":"started","message":"左腿在前做弓步蹲"}
        if t["status"] == "running_left":
            if kl < 110: t["cl"].append(kl)
            if len(t["cl"])>=5:
                t["status"]="running_right"
                t["left_score"]=max(0,100-(100-sum(t["cl"])/len(t["cl"]))*0.5)
                return {"fms_status":"step_complete","side":"left","score":round(t["left_score"],1),"message":"右侧弓步蹲"}
            return {"fms_status":"running","side":"left"}
        if t["status"] == "running_right":
            if kr < 110: t["cr"].append(kr)
            if len(t["cr"])>=5:
                t["right_score"]=max(0,100-(100-sum(t["cr"])/len(t["cr"]))*0.5)
                t["status"]="done"; t["completed"]=True
                t["data"]={"left_score":round(t["left_score"],1),"right_score":round(t["right_score"],1)}
                t["score"]=round(self.engine.score_symmetry(t["left_score"],t["right_score"]).score,1)
                return {"fms_status":"completed","left_score":round(t["left_score"],1),"right_score":round(t["right_score"],1),"score":t["score"],"body_observation":f"asymmetry diff {abs(t['left_score']-t['right_score']):.0f} pts"}
            return {"fms_status":"running","side":"right"}
        return {}

    def _generate_training_suggestions(self, scores, tags):
        s = {x.dimension:x.score for x in scores}
        sugs = []
        if s.get("balance",100)<60:
            sugs.append({"focus":"平衡能力","exercises":["单腿站立（睁眼→闭眼渐进）","Bosu球深蹲","单腿硬拉"],"frequency":"每周3次,每次3组","reason":f"balance score {s['balance']:.0f}"})
        if s.get("flexibility",100)<60:
            sugs.append({"focus":"下肢灵活性","exercises":["踝关节灵活性训练","髋关节打开训练","深蹲最低点保持"],"frequency":"每日进行","reason":f"flexibility score {s['flexibility']:.0f}"})
        if s.get("upper_limb",100)<60:
            sugs.append({"focus":"肩关节活动度","exercises":["墙壁天使","弹力带肩旋转","胸椎伸展"],"frequency":"每日进行","reason":f"shoulder score {s['upper_limb']:.0f}"})
        if s.get("core",100)<60:
            sugs.append({"focus":"核心力量","exercises":["死虫式","鸟狗式","平板支撑"],"frequency":"每周4次","reason":f"core score {s['core']:.0f}"})
        if s.get("symmetry",100)<60:
            sugs.append({"focus":"双侧对称性","exercises":["单侧弓步蹲（弱侧优先）","单腿臀桥","保加利亚分腿蹲"],"frequency":"每周3次","reason":f"symmetry score {s['symmetry']:.0f}"})
        if not sugs:
            sugs.append({"focus":"综合能力","exercises":["保持当前训练","逐渐增加强度","每月复测"],"frequency":"按现有处方","reason":"各项指标良好"})
        return sugs
