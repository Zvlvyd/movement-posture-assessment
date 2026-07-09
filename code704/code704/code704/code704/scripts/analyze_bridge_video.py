# -*- coding: utf-8 -*-
"""分析 臀桥_标准.mp4，与臀桥 FSM 对比"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2, numpy as np, json
from collections import Counter
from models.engine import model_manager
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import create_bridge_fsm, get_fsm_context, get_initial_state

VIDEO = r"d:\program\pythonProject\运动姿态评估与纠错系统\臀桥_标准.mp4"
print(f"视频: {os.path.basename(VIDEO)}, 存在: {os.path.exists(VIDEO)}")
cap = cv2.VideoCapture(VIDEO)
fps = cap.get(cv2.CAP_PROP_FPS)
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"FPS: {fps}, 总帧: {total}, 时长: {total/fps:.1f}s")

model_manager._ensure_loaded()
ac = AngleCalculator()
fsm = create_bridge_fsm()
fsm.start('down')

hip_vals, tt_vals, knee_vals, states = [], [], [], []
rep_frames, transitions = [], []
current = 'down'
lost = valid = 0
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret: break
    frame_idx += 1
    kp_xy, kp_conf = model_manager.get_keypoints(frame)
    if kp_xy is None: lost += 1; hip_vals.append(None); states.append(current); continue
    kp_xy = np.array(kp_xy)
    fk = np.zeros((17,3), dtype=np.float32); fk[:,:2] = kp_xy; fk[:,2] = kp_conf or 1.0
    if int(np.sum(fk[:,2] >= 0.15)) < 7: lost += 1; hip_vals.append(None); states.append(current); continue
    valid += 1
    angles = ac.compute_all_angles(fk)
    hip = angles.get('left_hip') or angles.get('right_hip')
    tt = angles.get('trunk_tilt')
    knee = angles.get('left_knee') or angles.get('right_knee')
    hip_vals.append(round(hip,1) if hip else None)
    tt_vals.append(round(tt,1) if tt else None)
    knee_vals.append(round(knee,1) if knee else None)
    if hip is None: states.append(current); continue
    ctx = get_fsm_context('bridge', angles)
    ns = fsm.update(ctx)
    if ns:
        if ns == 'complete':
            rep_frames.append(frame_idx)
            print(f'  ✅ REP #{len(rep_frames)} @ 帧{frame_idx}: hip={hip:.1f}°  {current}→{ns}')
        else:
            print(f'     {current}→{ns} @ 帧{frame_idx}: hip={hip:.1f}°')
        current = ns
    states.append(current)
cap.release()

vh = [x for x in hip_vals if x is not None]
vt = [x for x in tt_vals if x is not None]
vk = [x for x in knee_vals if x is not None]

print(f"\n{'='*60}")
print(f"有效帧: {valid}, 丢失: {lost}")
print(f"髋角(shoulder-hip-knee): {min(vh):.1f}°~{max(vh):.1f}°  均值:{np.mean(vh):.1f}°  std:{np.std(vh):.1f}°")
print(f"躯干倾斜: {min(vt):.1f}°~{max(vt):.1f}°  均值:{np.mean(vt):.1f}°  std:{np.std(vt):.1f}°")
print(f"膝角: {min(vk):.1f}°~{max(vk):.1f}°  均值:{np.mean(vk):.1f}°  std:{np.std(vk):.1f}°")

print(f"\nFSM 计数: {len(rep_frames)} reps")
print(f"状态分布:")
for s, c in Counter(states).items():
    print(f"  {s}: {c}帧 ({c/len(states)*100:.1f}%)")

# 每20帧采样输出
print(f"\n{'='*60}")
print(f"逐帧采样（每25帧）:")
print(f"{'帧':>5s} | {'髋角':>8s} | {'膝角':>8s} | {'tt':>7s} | {'状态':>10s} | 事件")
print("-" * 65)
prev = 'down'
for i in range(0, len(hip_vals), 25):
    h = hip_vals[i]; k = knee_vals[i]; t = tt_vals[i]; s = states[i]
    ev = ""
    if i+1 in rep_frames: ev = "✅ REP"
    elif s != prev: ev = f"→ {s}"
    prev = s
    hs = f"{h:.1f}°" if h else "None"; ks = f"{k:.1f}°" if k else "None"; ts = f"{t:.1f}°" if t else "None"
    print(f"{i+1:>5d} | {hs:>8s} | {ks:>8s} | {ts:>7s} | {s:>10s} | {ev}")

# FSM 阈值诊断
print(f"\n{'='*60}")
print(f"FSM 阈值 vs 实际髋角:")
issues = []
if max(vh) < 170: issues.append(f"最高髋角 {max(vh):.1f}° < 170°, lifting→up 永远无法触发")
if min(vh) > 130 and max(vh) < 130: issues.append(f"down→lifting 无法触发")
if issues:
    print("⚠️  不匹配:"); [print(f"  ❌ {i}") for i in issues]
else:
    print("✅ FSM 阈值与实际视频匹配")

# 标准角度对比
with open('models/knowledge/standard_actions.json','r',encoding='utf-8') as f:
    db = json.load(f)['actions']['臀桥']['standard_keypoints']['侧面']['target_angles']
print(f"\n标准 JSON 匹配:")
for k,v in db.items():
    vals = {'left_hip':vh, 'right_hip':vh, 'left_knee':vk, 'trunk_tilt':vt}.get(k, vh)
    ok = min(vals) >= v['min'] and max(vals) <= v['max'] if vals else False
    print(f"  {k}: JSON {v['min']}-{v['max']}°  视频 {min(vals) if vals else 0:.0f}-{max(vals) if vals else 0:.0f}°  {'✅' if ok else '❌'}")
