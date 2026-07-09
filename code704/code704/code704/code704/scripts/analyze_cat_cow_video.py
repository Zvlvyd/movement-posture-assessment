# -*- coding: utf-8 -*-
"""分析 猫牛式环绕_标准.mp4，与猫牛式 FSM 对比"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from collections import Counter
from models.engine import model_manager
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import create_cat_cow_fsm, get_fsm_context, get_initial_state

VIDEO_PATH = r"d:\program\pythonProject\运动姿态评估与纠错系统\猫牛式环绕_标准.mp4"

print(f"视频: {os.path.basename(VIDEO_PATH)}")
print(f"存在: {os.path.exists(VIDEO_PATH)}")
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"FPS: {fps}, 总帧: {total_frames}, 时长: {total_frames/fps:.1f}s")

model_manager._ensure_loaded()
ac = AngleCalculator()

fsm = create_cat_cow_fsm()
fsm.start('neutral')

hip_vals, tt_vals, states = [], [], []
rep_frames, transitions = [], []
lost = valid = 0
current = 'neutral'
prev = 'neutral'
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret: break
    frame_idx += 1
    kp_xy, kp_conf = model_manager.get_keypoints(frame)
    if kp_xy is None: lost += 1; hip_vals.append(None); tt_vals.append(None); states.append(current); continue
    kp_xy = np.array(kp_xy)
    fk = np.zeros((17,3), dtype=np.float32)
    fk[:,:2] = kp_xy; fk[:,2] = kp_conf if kp_conf else 1.0
    if int(np.sum(fk[:,2] >= 0.15)) < 7: lost += 1; hip_vals.append(None); tt_vals.append(None); states.append(current); continue
    valid += 1
    angles = ac.compute_all_angles(fk)
    hip = angles.get('left_hip') or angles.get('right_hip')
    tt = angles.get('trunk_tilt')
    hip_vals.append(round(hip, 1) if hip else None)
    tt_vals.append(round(tt, 1) if tt else None)
    if hip is None: states.append(current); continue
    ctx = get_fsm_context('cat_cow', angles)
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

v_hip = [x for x in hip_vals if x is not None]
v_tt = [x for x in tt_vals if x is not None]

print(f"\n{'='*60}")
print(f"有效帧: {valid}, 丢失: {lost}")
print(f"\n髋角(shoulder-hip-knee):")
if v_hip:
    print(f"  范围: {min(v_hip):.1f}° ~ {max(v_hip):.1f}°  均值: {np.mean(v_hip):.1f}°  std: {np.std(v_hip):.1f}°")
print(f"躯干倾斜(trunk_tilt):")
if v_tt:
    print(f"  范围: {min(v_tt):.1f}° ~ {max(v_tt):.1f}°  均值: {np.mean(v_tt):.1f}°  std: {np.std(v_tt):.1f}°")

print(f"\n猫牛式 FSM 计数: {len(rep_frames)} reps")
print(f"FSM 状态分布:")
for s, c in Counter(states).items():
    print(f"  {s}: {c} 帧 ({c/len(states)*100:.1f}%)")

# FSM 阈值诊断
print(f"\nFSM 阈值 vs 实际髋角:")
if v_hip:
    ma, mi = max(v_hip), min(v_hip)
    print(f"  neutral→cat:       hip < 150°  →  实际范围: {mi:.1f}° ~ {ma:.1f}°")
    print(f"  cat→cow:           hip > 170°  →  实际最高: {ma:.1f}°")
    print(f"  cow→complete:      150°≤hip≤170° → 实际中段")
    print(f"  complete→neutral:  hip < 145°  →  实际最低: {mi:.1f}°")
    print()
    issues = []
    if ma < 170: issues.append(f"最高髋角 {ma:.1f}° < 170°, cat→cow 永远无法触发")
    if mi > 150: issues.append(f"最低髋角 {mi:.1f}° > 150°, neutral→cat 永远无法触发")
    if issues:
        print("⚠️  FSM 不匹配:")
        for i in issues: print(f"  ❌ {i}")
    else:
        print("✅ FSM 阈值与实际视频匹配")

# 标准角度对比
import json
with open('models/knowledge/standard_actions.json','r',encoding='utf-8') as f:
    std = json.load(f)
db = std['actions']['猫牛式']['standard_keypoints']['侧面']['target_angles']
print(f"\n标准 JSON 角度:")
for k,v in db.items():
    print(f"  {k}: {v['min']}-{v['max']}° (optimal {v['optimal']}°)")
if v_tt:
    print(f"  视频 trunk_tilt: {min(v_tt):.1f}° ~ {max(v_tt):.1f}°")
    tt_ok = min(v_tt) >= db['trunk_tilt']['min'] and max(v_tt) <= db['trunk_tilt']['max']
    print(f"  {'✅ 匹配' if tt_ok else '❌ 不匹配'}")
if v_hip:
    print(f"  视频 hip: {min(v_hip):.1f}° ~ {max(v_hip):.1f}°")
    h_ok = min(v_hip) >= db['left_hip']['min'] and max(v_hip) <= db['left_hip']['max']
    print(f"  {'✅ 匹配' if h_ok else '❌ 不匹配'}")
