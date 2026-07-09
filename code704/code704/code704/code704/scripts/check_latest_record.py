# -*- coding: utf-8 -*-
"""查看最新学习记录的角度数据，用于调整 FSM"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from backend.database.connection import get_db, init_db

init_db()
db = next(get_db())

from backend.database import models

# 查询最新的 learning 类型记录
records = db.query(models.AssessmentRecord).filter(
    models.AssessmentRecord.assessment_type == 'learning',
    models.AssessmentRecord.user_id == 1  # admin 用户
).order_by(models.AssessmentRecord.id.desc()).limit(3).all()

print(f"最近 3 条学习记录:")
print()

for record in records:
    pd = json.loads(record.posture_data) if isinstance(record.posture_data, str) else (record.posture_data or {})
    rd = json.loads(record.rom_data) if isinstance(record.rom_data, str) else (record.rom_data or {})
    rpt = json.loads(record.report_data) if isinstance(record.report_data, str) else (record.report_data or {})

    action = pd.get('action', '?') if isinstance(pd, dict) else '?'
    view = pd.get('view', '?') if isinstance(pd, dict) else '?'

    print(f"  id={record.id} | {action} | 视角={view} | "
          f"score={record.overall_score:.1f} | "
          f"reps={rd.get('rep_count','?') if isinstance(rd,dict) else '?'} | "
          f"frames={rd.get('frame_count','?') if isinstance(rd,dict) else '?'}")

    # 找到最新的臀桥记录
    if '臀桥' in action or 'bridge' in action.lower():
        print(f"\n{'='*60}")
        print(f"🔍 臀桥记录 #{record.id} 详细分析")
        print(f"{'='*60}")

        angle_history = rpt.get('angle_history', []) if isinstance(rpt, dict) else []
        if not angle_history:
            angle_history = rd.get('angle_history', []) if isinstance(rd, dict) else []

        if angle_history:
            hip_vals = []
            for entry in angle_history:
                angles = entry.get('angles', {})
                hip = angles.get('left_hip') or angles.get('right_hip')
                if hip:
                    hip_vals.append((entry.get('frame', 0), hip, entry.get('score', 0)))

            if hip_vals:
                frames, hips, scores = zip(*hip_vals)
                print(f"\n  髋角统计 ({len(hip_vals)} 帧):")
                print(f"    范围: {min(hips):.1f}° ~ {max(hips):.1f}°")
                print(f"    均值: {np.mean(hips):.1f}°  标准差: {np.std(hips):.1f}°")

                # 标出可能的 rep 边界
                print(f"\n  逐帧髋角（每5帧采样，标注趋势）:")
                prev_hip = None
                direction = ''
                for i in range(0, len(hip_vals), 5):
                    f, h, s = hip_vals[i]
                    if prev_hip is not None:
                        direction = '↑' if h > prev_hip + 3 else ('↓' if h < prev_hip - 3 else '→')
                    print(f"    帧{f:>4d}: hip={h:>6.1f}° {direction}  score={s}")
                    prev_hip = h
        else:
            print("\n  ⚠️ 无角度历史数据")

        # 只有第一条臀桥记录时退出（最新）
        break

db.close()
