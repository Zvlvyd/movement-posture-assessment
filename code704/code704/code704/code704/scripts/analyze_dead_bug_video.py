# -*- coding: utf-8 -*-
"""分析 dead_bug_standard.mp4 的关键角度变化，与死虫式 FSM 对比"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import time
from models.engine import model_manager
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import create_dead_bug_fsm, get_fsm_context, get_initial_state

# 直接使用绝对路径
VIDEO_PATH = r"d:\program\pythonProject\运动姿态评估与纠错系统\dead_bug_standard .mp4"

print(f"视频路径: {VIDEO_PATH}")
print(f"视频存在: {os.path.exists(VIDEO_PATH)}")

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print(f"FPS: {fps}, 总帧数: {total_frames}, 时长: {total_frames/fps:.1f}s")

# 加载模型
print("正在加载 YOLO 模型...")
model_manager._ensure_loaded()
angle_calc = AngleCalculator()

# 初始化 FSM
fsm = create_dead_bug_fsm()
init_state = get_initial_state('dead_bug')
fsm.start(init_state)

# 收集数据
hip_angles = []
fsm_states = []
rep_frames = []
current_state = init_state

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1

    # YOLO 提取关键点 → (keypoints_xy, confidences) or (None, None)
    kp_xy, kp_conf = model_manager.get_keypoints(frame)
    if kp_xy is None:
        hip_angles.append(None)
        fsm_states.append(current_state)
        continue

    # 构建 17x3 数组
    kp_xy = np.array(kp_xy)
    full_kps = np.zeros((17, 3), dtype=np.float32)
    full_kps[:, :2] = kp_xy
    full_kps[:, 2] = kp_conf if kp_conf is not None else 1.0

    # 计算关节角度
    angles = angle_calc.compute_all_angles(full_kps)
    hip_angle = angles.get('left_hip') or angles.get('right_hip')

    if hip_angle is None:
        hip_angles.append(None)
        fsm_states.append(current_state)
        continue

    hip_angles.append(round(hip_angle, 1))

    # FSM 更新
    ctx = get_fsm_context('dead_bug', angles)
    new_state = fsm.update(ctx)
    if new_state:
        current_state = new_state
        if new_state == 'complete':
            rep_frames.append(frame_idx)
    fsm_states.append(current_state)

    if frame_idx % 50 == 0:
        print(f"  处理中... {frame_idx}/{total_frames} 帧")

cap.release()
print(f"处理完成，共 {frame_idx} 帧")

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

    # 检测到的 rep
    print(f"\n死虫式 FSM 计数: {len(rep_frames)} reps")
    if rep_frames:
        print(f"  Complete 帧号: {rep_frames[:20]}")

    # FSM 状态分布
    from collections import Counter
    state_counts = Counter(fsm_states)
    print(f"\nFSM 状态分布:")
    for s, c in state_counts.items():
        print(f"  {s}: {c} 帧 ({c/len(fsm_states)*100:.1f}%)")

# ── 输出逐帧角度变化（每 5 帧采样，便于观察趋势） ──
print(f"\n{'='*60}")
print(f"逐帧髋角变化（每 10 帧采样）:")
print(f"{'帧号':>6s} | {'髋角':>8s} | {'FSM状态':>12s} | 事件")
print("-" * 55)
for i in range(0, len(hip_angles), 10):
    a = hip_angles[i] if i < len(hip_angles) else None
    s = fsm_states[i] if i < len(fsm_states) else '?'
    event = ""
    if i+1 in rep_frames:
        event = "✅ REP COUNT"
    elif i >= 1 and fsm_states[i] != fsm_states[i-1]:
        event = f"→ {fsm_states[i]}"
    a_str = f"{a:.1f}°" if a is not None else "None"
    print(f"{i+1:>6d} | {a_str:>8s} | {s:>12s} | {event}")

# ── FSM 阈值对比 ──
print(f"\n{'='*60}")
print(f"FSM 阈值 vs 实际角度:")
print(f"  ready → extending:  髋角 < 160°  →  实际最低: {min(valid_angles):.1f}°")
print(f"  extending → extended: 髋角 < 130°  →  实际最低: {min(valid_angles):.1f}°")
print(f"  extended → complete: 髋角 > 155°  →  实际最高: {max(valid_angles):.1f}°")
print(f"  complete → extending: 髋角 < 140°  →  触发下一轮")

# ── 判断是否符合 ──
print(f"\n{'='*60}")
min_a, max_a = min(valid_angles), max(valid_angles)
issues = []
if max_a < 155:
    issues.append(f"最大髋角 {max_a:.1f}° < 155°，永远无法触发 extended→complete")
if min_a > 130:
    issues.append(f"最小髋角 {min_a:.1f}° > 130°，永远无法触发 extending→extended")
if max_a < 160:
    issues.append(f"最大髋角 {max_a:.1f}° < 160°，可能无法从 ready 启动")
if min_a > 140:
    issues.append(f"最小髋角 {min_a:.1f}° > 140°，complete→extending 可能触发困难")

if issues:
    print("⚠️  FSM 与视频不匹配！问题：")
    for issue in issues:
        print(f"  ❌ {issue}")
else:
    print("✅ FSM 阈值与实际视频角度变化基本匹配")
