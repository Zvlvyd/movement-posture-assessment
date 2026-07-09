# -*- coding: utf-8 -*-
"""分析 髋部环绕_标准.mp4 的关键角度变化，与髋关节环绕 FSM 对比"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import time
from collections import Counter
from models.engine import model_manager
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import create_hip_circle_fsm, get_fsm_context, get_initial_state

VIDEO_PATH = r"d:\program\pythonProject\运动姿态评估与纠错系统\髋部环绕_标准.mp4"

print(f"视频路径: {VIDEO_PATH}")
print(f"视频存在: {os.path.exists(VIDEO_PATH)}")

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"FPS: {fps}, 总帧数: {total_frames}, 时长: {total_frames/fps:.1f}s")

print("正在加载 YOLO 模型...")
model_manager._ensure_loaded()
angle_calc = AngleCalculator()

# 初始化 FSM
fsm = create_hip_circle_fsm()
init_state = get_initial_state('hip_circle')
fsm.start(init_state)

# 收集数据
hip_angles = []
fsm_states = []
rep_frames = []
current_state = init_state
valid_kp_frames = 0
lost_kp_frames = 0

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1

    kp_xy, kp_conf = model_manager.get_keypoints(frame)
    if kp_xy is None:
        hip_angles.append(None)
        fsm_states.append(current_state)
        lost_kp_frames += 1
        continue

    kp_xy = np.array(kp_xy)
    full_kps = np.zeros((17, 3), dtype=np.float32)
    full_kps[:, :2] = kp_xy
    full_kps[:, 2] = kp_conf if kp_conf is not None else 1.0

    valid_kp_count = int(np.sum(full_kps[:, 2] >= 0.15))
    if valid_kp_count < 7:
        hip_angles.append(None)
        fsm_states.append(current_state)
        lost_kp_frames += 1
        continue

    valid_kp_frames += 1
    angles = angle_calc.compute_all_angles(full_kps)
    hip_angle = angles.get('left_hip') or angles.get('right_hip')

    if hip_angle is None:
        hip_angles.append(None)
        fsm_states.append(current_state)
        continue

    hip_angles.append(round(hip_angle, 1))

    # FSM 更新
    ctx = get_fsm_context('hip_circle', angles)
    new_state = fsm.update(ctx)
    if new_state:
        current_state = new_state
        if new_state == 'complete':
            rep_frames.append(frame_idx)
    fsm_states.append(current_state)

    if frame_idx % 100 == 0:
        print(f"  处理中... {frame_idx}/{total_frames} 帧")

cap.release()
print(f"处理完成，共 {frame_idx} 帧，有效关键点帧: {valid_kp_frames}, 丢失: {lost_kp_frames}")

# ── 输出分析 ──
valid_angles = [a for a in hip_angles if a is not None]
if valid_angles:
    print(f"\n{'='*60}")
    print(f"髋关节角度统计:")
    print(f"  最小值: {min(valid_angles):.1f}°")
    print(f"  最大值: {max(valid_angles):.1f}°")
    print(f"  平均值: {np.mean(valid_angles):.1f}°")
    print(f"  标准差: {np.std(valid_angles):.1f}°")
    print(f"  有效帧: {len(valid_angles)}/{frame_idx}")

    print(f"\n髋关节环绕 FSM 计数: {len(rep_frames)} reps")
    if rep_frames:
        print(f"  Complete 帧号: {rep_frames}")

    state_counts = Counter(fsm_states)
    print(f"\nFSM 状态分布:")
    for s, c in state_counts.items():
        print(f"  {s}: {c} 帧 ({c/len(fsm_states)*100:.1f}%)")

# ── 逐帧角度变化（每 15 帧采样）──
print(f"\n{'='*60}")
print(f"逐帧髋角变化（每 15 帧采样）:")
print(f"{'帧号':>6s} | {'髋角':>8s} | {'FSM状态':>12s} | 事件")
print("-" * 55)
prev_state = init_state
for i in range(0, len(hip_angles), 15):
    a = hip_angles[i] if i < len(hip_angles) else None
    s = fsm_states[i] if i < len(fsm_states) else '?'
    event = ""
    if i+1 in rep_frames:
        event = "✅ REP COUNT"
    elif s != prev_state:
        event = f"→ {s}"
    prev_state = s
    a_str = f"{a:.1f}°" if a is not None else "None"
    print(f"{i+1:>6d} | {a_str:>8s} | {s:>12s} | {event}")

# ── FSM 阈值对比 ──
print(f"\n{'='*60}")
print(f"FSM 阈值 vs 实际角度:")
if valid_angles:
    min_a, max_a = min(valid_angles), max(valid_angles)
    print(f"  rest → moving:      hip < 140°   →  实际: {min_a:.1f}° ~ {max_a:.1f}°")
    print(f"  moving → extended:  hip < 128°   →  实际最低: {min_a:.1f}°")
    print(f"  extended → returning: hip > 145°  →  实际最高: {max_a:.1f}°")
    print(f"  returning → complete: hip > 155°  →  实际最高: {max_a:.1f}°")
    print(f"  complete → rest:    hip < 138°   →  实际最低: {min_a:.1f}°")

    # 问题诊断
    print(f"\n{'='*60}")
    issues = []
    if min_a > 128:
        issues.append(f"最小髋角 {min_a:.1f}° > 128°，永远无法触发 moving→extended")
    if max_a < 155:
        issues.append(f"最大髋角 {max_a:.1f}° < 155°，永远无法触发 returning→complete")
    if min_a > 140:
        issues.append(f"最小髋角 {min_a:.1f}° > 140°，可能无法触发 complete→rest")
    if max_a < 145:
        issues.append(f"最大髋角 {max_a:.1f}° < 145°，永远无法触发 extended→returning")
    if min_a > 140:
        issues.append(f"最小髋角 {min_a:.1f}° > 140°，可能无法触发 rest→moving")

    if issues:
        print("⚠️  FSM 与视频不匹配！")
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("✅ FSM 阈值与实际视频角度变化基本匹配")
    print()
    print(f"标准角度 (standard_actions.json): left_hip/right_hip 120-170° (optimal 150°)")
    print(f"视频实际: {min_a:.1f}° ~ {max_a:.1f}° (mean {np.mean(valid_angles):.1f}°)")
