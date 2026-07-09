# -*- coding: utf-8 -*-
"""处理臀桥_标准.mp4，叠加骨架 + 髋角/FSM状态标注"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from models.engine import model_manager
from models.angle_calculator import AngleCalculator
from models.action_recognizer.squat_fsm import create_bridge_fsm, get_fsm_context, get_initial_state

INPUT = r"d:\program\pythonProject\运动姿态评估与纠错系统\臀桥_标准.mp4"
OUTPUT = r"d:\program\pythonProject\运动姿态评估与纠错系统\臀桥_标准_骨架.mp4"

model_manager._ensure_loaded()
ac = AngleCalculator()
fsm = create_bridge_fsm()
fsm.start('down')

cap = cv2.VideoCapture(INPUT)
fps = cap.get(cv2.CAP_PROP_FPS)
fw = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
fh = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT, fourcc, fps, (fw, fh))

SKELETON = [
    (5,6),(5,7),(7,9),(6,8),(8,10),          # 上肢
    (5,11),(6,12),(11,12),                     # 躯干
    (11,13),(13,15),(12,14),(14,16),           # 下肢
    (0,1),(0,2),(1,3),(2,4),                   # 面部
]

current = 'down'
rep_count = 0
frame_idx = 0

while True:
    ret, frame = cap.read()
    if not ret: break
    frame_idx += 1

    kp_xy, kp_conf = model_manager.get_keypoints(frame)
    overlay = frame.copy()

    if kp_xy is not None:
        kp_xy = np.array(kp_xy)

        # 画骨架
        for i, j in SKELETON:
            if i < len(kp_xy) and j < len(kp_xy):
                x1, y1 = int(kp_xy[i][0]), int(kp_xy[i][1])
                x2, y2 = int(kp_xy[j][0]), int(kp_xy[j][1])
                if x1 > 0 and y1 > 0 and x2 > 0 and y2 > 0:
                    cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 100), 2)

        # 画关键点
        for i in range(len(kp_xy)):
            x, y = int(kp_xy[i][0]), int(kp_xy[i][1])
            if x > 0 and y > 0:
                cv2.circle(overlay, (x, y), 4, (0, 255, 100), -1)
                cv2.circle(overlay, (x, y), 5, (255, 255, 255), 1)

        # 计算角度 + FSM
        fk = np.zeros((17,3), dtype=np.float32)
        fk[:,:2] = kp_xy
        fk[:,2] = kp_conf or 1.0
        angles = ac.compute_all_angles(fk)
        hip = angles.get('left_hip') or angles.get('right_hip')
        if hip:
            ctx = get_fsm_context('bridge', angles)
            ns = fsm.update(ctx)
            if ns:
                if ns == 'complete': rep_count += 1
                current = ns

            # 左上角：髋角 + 状态 + rep
            color = (0, 255, 100) if 'complete' in current or 'up' in current else (200, 200, 200)
            cv2.putText(overlay, f"Hip: {hip:.1f}", (12, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(overlay, f"State: {current}", (12, 60),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            cv2.putText(overlay, f"Reps: {rep_count}", (12, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

    out.write(overlay)
    if frame_idx % 50 == 0:
        print(f"  渲染中... {frame_idx}/{total}")

cap.release()
out.release()
print(f"完成！输出: {OUTPUT}")
print(f"文件大小: {os.path.getsize(OUTPUT)/1024/1024:.1f} MB")
