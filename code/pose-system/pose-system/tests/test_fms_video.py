# -*- coding: utf-8 -*-
"""
FMS 本地视频离线测试工具
=========================
用法:
  # 单项测试（指定 --test-idx 0~4）
  python tests/test_fms_video.py -i test_data/fms_0.mp4 --test-idx 0

  # 一键测试全部 5 项（自动读取 test_data/fms_*.mp4）
  python tests/test_fms_video.py --test-all

  # 完整参数
  python tests/test_fms_video.py -i 视频.mp4 --test-idx 1 -o output.mp4 -j output.json -m yolov8s-pose.pt

FMS 5 项测试:
  0. 闭眼单腿站立 — fms_0.mp4
  1. 徒手过头深蹲 — fms_1.mp4
  2. 肩关节活动度 — fms_2.mp4
  3. 平板支撑   — fms_3.mp4
  4. 弓步蹲对称 — fms_4.mp4
"""

import sys, os
# tests/ 目录下的脚本，需要将项目根目录加入 sys.path 才能 import models 等
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import json
import argparse
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from models.yolo_pose_engine import YOLOPoseEngine
from models.angle_calculator import AngleCalculator
from models.fms.scoring import FMSScoringEngine, Score

# 用帧计数代替 time.time()，避免批处理时墙钟计时失真
def _frame_time(frame_count: int, fps: float = 30.0) -> float:
    return frame_count / max(fps, 1)


# ═══════════════════════════════════════════════════════════
# COCO 关键点索引 & 骨架连接
# ═══════════════════════════════════════════════════════════
SKELETON = [
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)
]

KEYPOINT_NAMES = {
    0: "nose", 1: "left_eye", 2: "right_eye", 3: "left_ear", 4: "right_ear",
    5: "left_shoulder", 6: "right_shoulder", 7: "left_elbow", 8: "right_elbow",
    9: "left_wrist", 10: "right_wrist", 11: "left_hip", 12: "right_hip",
    13: "left_knee", 14: "right_knee", 15: "left_ankle", 16: "right_ankle",
}

FMS_TEST_NAMES = {
    0: "闭眼单腿站立",
    1: "徒手过头深蹲",
    2: "肩关节活动度",
    3: "平板支撑",
    4: "弓步蹲对称",
}


class OfflineFMSState:
    """离线 FMS 状态机。可指定 test_idx 只评估单项。"""

    def __init__(self, test_idx: Optional[int] = None):
        self.test_filter = test_idx  # None = 全部, int = 仅此项
        self.tests = [
            {"idx": i, "name": FMS_TEST_NAMES[i],
             "status": "pending", "start_time": 0, "data": None,
             "score": 0, "completed": False}
            for i in range(5)
        ]

    def current(self, idx: int):
        return self.tests[idx] if idx < len(self.tests) else None

    def all_completed(self) -> bool:
        if self.test_filter is not None:
            return self.tests[self.test_filter].get("completed", False)
        return all(t.get("completed") for t in self.tests)

    def mark_others_skipped(self):
        """单项模式下将其余 4 项标记为跳过。"""
        if self.test_filter is not None:
            for i in range(5):
                if i != self.test_filter:
                    self.tests[i]["status"] = "skipped"
                    self.tests[i]["completed"] = True
                    self.tests[i]["score"] = 0


class OfflineFMSEvaluator:
    """离线 FMS 评估器。test_idx=None 评估全部5项，test_idx=0~4 仅评估单项。"""

    def __init__(self, angle_calc: AngleCalculator, scoring_engine: FMSScoringEngine,
                 test_idx: Optional[int] = None, fps: float = 30.0):
        self.angle_calc = angle_calc
        self.engine = scoring_engine
        self.test_idx = test_idx
        self.fps = fps
        self.state = OfflineFMSState(test_idx)
        if test_idx is not None:
            self.state.mark_others_skipped()
        self.frame_results: List[dict] = []

    def _dur(self, start_frame: int, current_frame: int) -> float:
        """通过帧差计算真实视频时间（秒）。"""
        return (current_frame - start_frame) / max(self.fps, 1)

    def evaluate_frame(self, keypoints: np.ndarray, frame_idx: int) -> dict:
        """对单帧运行评估。"""
        angles = self.angle_calc.compute_all_angles(keypoints)
        frame_eval = {"frame": frame_idx, "angles": {}, "tests": {}}

        for k, v in angles.items():
            if v is not None:
                frame_eval["angles"][k] = round(v, 1)

        # 体态比例因子（用于自适应阈值）
        body_scale = self._body_scale(keypoints)

        run_tests = [self.test_idx] if self.test_idx is not None else range(5)

        for test_idx in run_tests:
            test = self.state.current(test_idx)
            if test.get("completed") or test.get("status") == "skipped":
                frame_eval["tests"][test_idx] = {"status": test["status"], "score": test.get("score", 0)}
                continue

            if test_idx == 0:
                result = self._eval_balance(test, angles, keypoints, body_scale, frame_idx)
            elif test_idx == 1:
                result = self._eval_squat(test, angles, keypoints)
            elif test_idx == 2:
                result = self._eval_shoulder(test, angles, keypoints, body_scale)
            elif test_idx == 3:
                result = self._eval_plank(test, angles, keypoints, body_scale, frame_idx)
            elif test_idx == 4:
                result = self._eval_symmetry(test, angles, keypoints)
            else:
                result = {}

            frame_eval["tests"][test_idx] = result

        self.frame_results.append(frame_eval)
        return frame_eval

    @staticmethod
    def _body_scale(kps: np.ndarray) -> float:
        """根据肩-髋距离估算体态缩放因子（像素 → 归一化）。"""
        ls = kps[5] if len(kps) > 5 else [0, 0]
        lh = kps[11] if len(kps) > 11 else [0, 0]
        torso_h = abs(ls[1] - lh[1]) if ls[1] > 0 and lh[1] > 0 else 100
        return max(torso_h, 30)  # 至少 30px，防止除零

    # ── 评估 0: 闭眼单腿站立 ──────────────────────
    def _eval_balance(self, test: dict, angles, kps, body_scale: float, frame_idx: int) -> dict:
        la = kps[15][1] if len(kps) > 15 and kps[15][1] > 0 else 0
        ra = kps[16][1] if len(kps) > 16 and kps[16][1] > 0 else 0
        ankle_diff = abs(la - ra) if la > 0 and ra > 0 else 0
        # 自适应阈值：脚踝高度差 > 躯干长度的 25%（而非固定 40px）
        one_leg_up = ankle_diff > body_scale * 0.25

        if test["status"] == "pending":
            if one_leg_up:
                test["status"] = "running"
                test["start_frame"] = frame_idx
                return {"status": "started", "message": "单腿站立开始计时"}
            return {"status": "ready", "message": "等待单腿站立"}

        if test["status"] == "running":
            dur = self._dur(test.get("start_frame", 0), frame_idx)
            if not one_leg_up and dur > 1:
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"duration_sec": round(dur, 1)}
                test["score"] = round(self.engine.score_balance(dur).score, 1)
                return {"status": "completed", "duration_sec": round(dur, 1),
                        "score": test["score"], "message": f"保持 {dur:.1f}s"}
            if dur >= 30:
                test["status"] = "done"; test["completed"] = True
                test["data"] = {"duration_sec": 30.0}
                test["score"] = 100.0
                return {"status": "completed", "duration_sec": 30.0,
                        "score": 100.0, "message": "满分！"}
            return {"status": "running", "duration_sec": round(dur, 1),
                    "ankle_diff": round(ankle_diff, 1)}
        return {}

    # ── 评估 1: 徒手过头深蹲 ──────────────────────
    def _eval_squat(self, test: dict, angles, kps) -> dict:
        lk = angles.get("left_knee") or 180
        rk = angles.get("right_knee") or 180
        knee = min(lk, rk)

        if test["status"] == "pending":
            if knee < 130:
                test["status"] = "running"
                test["knee_vals"] = []
                return {"status": "started", "message": "检测到深蹲姿态"}
            return {"status": "ready", "message": "等待深蹲"}

        if test["status"] == "running":
            if knee < 120:
                test.setdefault("knee_vals", []).append(knee)
            # 膝盖角度低于 90° 或采集到足够深度
            if knee < 90 and len(test.get("knee_vals", [])) >= 3:
                avg = sum(test["knee_vals"]) / len(test["knee_vals"])
                test["status"] = "done"
                test["completed"] = True
                test["data"] = {"depth_angle": round(avg, 1)}
                test["score"] = round(self.engine.score_flexibility(avg, 0, 1.0).score, 1)
                return {"status": "completed", "depth_angle": round(avg, 1),
                        "score": test["score"], "message": f"最深角度 {avg:.1f}°"}
            return {"status": "running", "knee_angle": round(knee, 1)}
        return {}

    # ── 评估 2: 肩关节活动度 ──────────────────────
    def _eval_shoulder(self, test: dict, angles, kps, body_scale: float) -> dict:
        lw_y = kps[9][1] if len(kps) > 9 and kps[9][1] > 0 else 0
        rw_x = kps[10][0] if len(kps) > 10 and kps[10][0] > 0 else 0
        lw_x = kps[9][0] if len(kps) > 9 and kps[9][0] > 0 else 0
        ls_y = kps[5][1] if len(kps) > 5 and kps[5][1] > 0 else 0
        # 左手腕在肩部上方（自适应阈值）
        behind = lw_y < ls_y + body_scale * 0.2 if lw_y > 0 and ls_y > 0 else False

        if test["status"] == "pending":
            if behind:
                test["status"] = "running"
                test["poses"] = 0
                test["dists"] = []
                return {"status": "started", "message": "检测到背后触手姿态"}
            return {"status": "ready", "message": "等待背后触手"}

        if test["status"] == "running":
            if behind:
                test.setdefault("poses", 0)
                test["poses"] += 1
                dist = abs(rw_x - lw_x) if rw_x > 0 and lw_x > 0 else 999
                test.setdefault("dists", []).append(dist)
                if test["poses"] >= 5:
                    avg = sum(test["dists"]) / len(test["dists"])
                    # 归一化：距离 / 躯干长度 → 比值越小越好
                    norm_dist = avg / body_scale
                    test["status"] = "done"
                    test["completed"] = True
                    test["data"] = {"hand_dist_px": round(avg, 1), "ratio": round(norm_dist, 2)}
                    # 用归一化比值评分（<0.5 满分，>2.0 零分）
                    sc = max(0, min(100, (2.0 - norm_dist) / 1.5 * 100))
                    test["score"] = round(sc, 1)
                    return {"status": "completed", "hand_dist_ratio": round(norm_dist, 2),
                            "score": test["score"], "message": f"双手距比 {norm_dist:.2f}"}
                return {"status": "running", "hand_dist_px": round(dist, 1)}
            return {"status": "running", "message": "保持触手姿态"}
        return {}

    # ── 评估 3: 平板支撑 ──────────────────────────
    def _eval_plank(self, test: dict, angles, kps, body_scale: float, frame_idx: int) -> dict:
        trunk = angles.get("trunk_tilt") or 180
        ls_y = kps[5][1] if len(kps) > 5 and kps[5][1] > 0 else 0
        la_y = kps[15][1] if len(kps) > 15 and kps[15][1] > 0 else 0
        y_diff_ok = abs(ls_y - la_y) < body_scale * 1.5 if ls_y > 0 and la_y > 0 else False
        trunk_horizontal = trunk > 50 if trunk < 180 else False
        horizontal = trunk_horizontal or y_diff_ok

        if test["status"] == "pending":
            if horizontal:
                test["status"] = "running"
                test["start_frame"] = frame_idx
                return {"status": "started", "message": "平板支撑开始计时"}
            return {"status": "ready", "message": "等待平板支撑"}

        if test["status"] == "running":
            dur = self._dur(test.get("start_frame", 0), frame_idx)
            if not horizontal and dur > 1:
                test["status"] = "done"; test["completed"] = True
                test["data"] = {"duration_sec": round(dur, 1)}
                test["score"] = round(self.engine.score_core(dur).score, 1)
                return {"status": "completed", "duration_sec": round(dur, 1),
                        "score": test["score"], "message": f"保持 {dur:.1f}s"}
            return {"status": "running", "duration_sec": round(dur, 1)}
        return {}

    # ── 评估 4: 弓步蹲对称 ────────────────────────
    def _eval_symmetry(self, test: dict, angles, kps) -> dict:
        lk = angles.get("left_knee") or 180
        rk = angles.get("right_knee") or 180

        if test["status"] == "pending":
            if lk < 120:
                test["status"] = "running_left"
                test["cl"] = []
                test["cr"] = []
                return {"status": "started", "side": "left", "message": "左侧弓步开始"}
            return {"status": "ready", "message": "等待弓步蹲"}

        if test["status"] == "running_left":
            if lk < 120:
                test.setdefault("cl", []).append(lk)
            if len(test.get("cl", [])) >= 3:
                left_avg = sum(test["cl"]) / len(test["cl"])
                test["left_score"] = max(0, 100 - abs(90 - left_avg))
                test["status"] = "running_right"
                return {"status": "step_complete", "side": "left",
                        "left_avg_angle": round(left_avg, 1),
                        "message": "左侧完成，请换右侧"}

        if test["status"] == "running_right":
            if rk < 120:
                test.setdefault("cr", []).append(rk)
            if len(test.get("cr", [])) >= 3:
                right_avg = sum(test["cr"]) / len(test["cr"])
                test["right_score"] = max(0, 100 - abs(90 - right_avg))
                test["status"] = "done"
                test["completed"] = True
                symmetry_score = round(self.engine.score_symmetry(
                    test["left_score"], test["right_score"]).score, 1)
                test["score"] = symmetry_score
                test["data"] = {"left_avg": round(left_avg := test["left_score"], 1),
                                "right_avg": round(right_avg := test["right_score"], 1)}
                return {"status": "completed",
                        "left_avg_angle": round(test["left_score"], 1),
                        "right_avg_angle": round(test["right_score"], 1),
                        "score": symmetry_score,
                        "message": f"对称性得分: {symmetry_score}"}
        return {}

    def finalize(self, last_frame: int):
        """视频结束时调用：用帧计数将仍在 running 的测试收尾。"""
        for test_idx in range(5):
            test = self.state.current(test_idx)
            if test.get("completed") or test.get("status") == "skipped":
                continue
            if test.get("status") == "running":
                dur = self._dur(test.get("start_frame", 0), last_frame)
                if dur > 1:
                    if test_idx == 0:  # balance
                        test["status"] = "done"; test["completed"] = True
                        test["data"] = {"duration_sec": round(dur, 1)}
                        test["score"] = round(self.engine.score_balance(dur).score, 1)
                    elif test_idx == 3:  # plank
                        test["status"] = "done"; test["completed"] = True
                        test["data"] = {"duration_sec": round(dur, 1)}
                        test["score"] = round(self.engine.score_core(dur).score, 1)

    def get_summary(self) -> dict:
        """生成综合评分报告。跳过的测试不参与综合评分。"""
        scores = []
        details = {}
        for test in self.state.tests:
            name = FMS_TEST_NAMES.get(test["idx"], f"test{test['idx']}")
            is_skipped = test.get("status") == "skipped"
            if test.get("completed") and not is_skipped:
                sc = test.get("score", 0)
                dim_map = {0: "balance", 1: "flexibility", 2: "upper_limb",
                           3: "core", 4: "symmetry"}
                dim = dim_map.get(test["idx"], f"dim{test['idx']}")
                scores.append(Score(dim, sc))
                details[name] = {
                    "score": sc,
                    "data": test.get("data"),
                    "frames_evaluated": sum(
                        1 for fr in self.frame_results
                        if fr["tests"].get(test["idx"], {}).get("status") in
                        ("started", "running", "completed")
                    ),
                }
            elif is_skipped:
                details[name] = {"score": None, "status": "skipped"}
            else:
                details[name] = {"score": None, "status": test.get("status", "pending")}

        overall = self.engine.compute_overall(scores) if scores else 0
        risk = self.engine.get_risk_level(overall, scores)

        return {
            "overall_score": overall,
            "risk_level": risk,
            "dimension_scores": {s.dimension: s.score for s in scores},
            "details": details,
            "total_frames": len(self.frame_results),
        }


def draw_fms_overlay(frame: np.ndarray, frame_eval: dict, summary: dict = None) -> np.ndarray:
    """在视频帧上绘制 FMS 评估信息叠加层。"""
    h, w = frame.shape[:2]

    # ── 左上角：测试状态面板 ──
    overlay = frame.copy()
    panel_w = 280
    panel_h = 200
    cv2.rectangle(overlay, (8, 8), (8 + panel_w, 8 + panel_h), (0, 0, 0), -1)
    frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)

    y = 30
    for test_idx in range(5):
        name = FMS_TEST_NAMES[test_idx]
        test_info = frame_eval.get("tests", {}).get(test_idx, {})
        status = test_info.get("status", "pending")

        if status == "completed":
            color = (0, 255, 0)
            label = f"✓ {name}: {test_info.get('score', 0)}分"
        elif status in ("started", "running", "step_complete"):
            color = (0, 255, 255)
            msg = test_info.get("message", "")[:15]
            label = f"▶ {name}: {msg}"
        elif status == "skipped":
            color = (128, 128, 128)
            label = f"⊘ {name}: 跳过"
        else:
            color = (180, 180, 180)
            label = f"○ {name}"

        cv2.putText(frame, label, (16, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, color, 1, cv2.LINE_AA)
        y += 24

    # ── 右上角：当前帧角度 ──
    angles = frame_eval.get("angles", {})
    ay = 30
    for k, v in list(angles.items())[:8]:
        cv2.putText(frame, f"{k}: {v}°", (w - 180, ay),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
        ay += 20

    # ── 底部：综合评分（如果有） ──
    if summary:
        cv2.rectangle(frame, (0, h - 40), (w, h), (0, 0, 0), -1)
        text = f"FMS Overall: {summary['overall_score']} | Risk: {summary['risk_level']}"
        cv2.putText(frame, text, (16, h - 12), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 255), 1, cv2.LINE_AA)

    return frame


def process_video(
    input_path: str,
    output_path: Optional[str] = None,
    output_json: Optional[str] = None,
    model_path: str = "yolov8n-pose.pt",
    device: str = "auto",
    show: bool = False,
    skip_frames: int = 1,
    test_idx: Optional[int] = None,
) -> dict:
    """
    主处理函数：加载视频 → 逐帧检测 → FMS 评估 → 输出。

    test_idx: None=全部5项, 0~4=仅评估指定项
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"视频文件不存在: {input_path}")

    test_label = FMS_TEST_NAMES.get(test_idx, "全部5项") if test_idx is not None else "全部5项"
    print(f"=" * 60)
    print(f"  FMS 本地视频离线测试")
    print(f"  输入: {input_path}")
    print(f"  测试项: {test_label}")
    print(f"  模型: {model_path}")
    print(f"  设备: {device}")
    print(f"=" * 60)

    # 初始化
    print("\n[1/4] 加载 YOLO-Pose 模型...")
    yolo = YOLOPoseEngine(model_path=model_path, device=device)
    angle_calc = AngleCalculator()
    scoring = FMSScoringEngine()

    # 打开视频
    cap = cv2.VideoCapture(input_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  分辨率: {width}x{height}  FPS: {fps:.1f}  总帧数: {total}")

    evaluator = OfflineFMSEvaluator(angle_calc, scoring, test_idx=test_idx, fps=fps)

    # 输出视频
    out = None
    if output_path:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        print(f"  输出视频: {output_path}")

    # 处理帧
    print(f"\n[2/4] 逐帧处理（每 {skip_frames} 帧检测一次）...")
    frame_idx = 0
    processed = 0
    persons_detected = 0
    last_summary = None

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_idx += 1
        if frame_idx % skip_frames != 0:
            if out:
                out.write(frame)
            continue

        processed += 1

        # YOLO 检测
        persons, _ = yolo.process_frame(frame)

        if persons:
            persons_detected += 1
            kps = np.array(persons[0]["keypoints"])

            # FMS 评估
            frame_eval = evaluator.evaluate_frame(kps, frame_idx)

            # 绘制骨架
            frame = yolo.draw_keypoints(frame, persons)

            # 绘制 FMS 叠加层
            if evaluator.state.all_completed():
                if last_summary is None:
                    last_summary = evaluator.get_summary()
            frame = draw_fms_overlay(frame, frame_eval, last_summary)
        else:
            # 无人检测 — 写入空结果
            evaluator.frame_results.append({"frame": frame_idx, "angles": {}, "tests": {}, "no_person": True})

        if out:
            out.write(frame)

        if show:
            cv2.imshow("FMS Video Test", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        if processed % 30 == 0:
            pct = frame_idx / max(total, 1) * 100
            print(f"  进度: {frame_idx}/{total} ({pct:.0f}%)  "
                  f"检测到人体: {persons_detected}/{processed} 帧")

    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()

    # 生成报告
    print(f"\n[3/4] 生成 FMS 评估报告...")
    evaluator.finalize(frame_idx)  # 收尾仍在 running 的测试
    summary = evaluator.get_summary()

    print(f"\n{'=' * 50}")
    print(f"  FMS 综合评估报告")
    print(f"{'=' * 50}")
    print(f"  总帧数: {frame_idx}  |  处理帧数: {processed}")
    print(f"  检测到人体: {persons_detected} 帧 "
          f"({persons_detected / max(processed, 1) * 100:.0f}%)")
    print(f"  综合评分: {summary['overall_score']} 分")
    print(f"  风险等级: {summary['risk_level']}")
    print(f"  ---")
    for dim, sc in summary['dimension_scores'].items():
        print(f"  {dim}: {sc} 分")
    print(f"  ---")
    for name, detail in summary['details'].items():
        st = detail.get('status', '')
        if detail.get('score') is not None:
            print(f"  {name}: {detail['score']} 分  ({detail.get('frames_evaluated', 0)} 帧)")
        else:
            print(f"  {name}: 未完成 (状态: {st})")
    print(f"{'=' * 50}")

    # 保存 JSON
    if output_json:
        print(f"\n[4/4] 保存结果到 {output_json} ...")
        output_data = {
            "video_info": {
                "path": input_path,
                "width": width, "height": height,
                "fps": fps, "total_frames": total,
            },
            "processing": {
                "frames_processed": processed,
                "frames_with_person": persons_detected,
                "model": model_path,
                "device": device,
            },
            "summary": summary,
            "frame_results": evaluator.frame_results,
        }
        with open(output_json, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False,
                      default=lambda o: float(o) if isinstance(o, (np.float32, np.float64)) else str(o))
        print(f"  已保存 {len(evaluator.frame_results)} 帧结果")

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="FMS 本地视频离线测试工具 — 用本地视频评估 FMS 分析能力")
    parser.add_argument("--input", "-i", type=str, default=None,
                        help="输入视频路径（单项测试时使用）")
    parser.add_argument("--test-idx", "-t", type=int, choices=[0, 1, 2, 3, 4], default=None,
                        help="FMS 测试编号 (0=单腿站立 1=深蹲 2=肩关节 3=平板 4=弓步蹲)")
    parser.add_argument("--test-all", action="store_true",
                        help="一键测试全部 5 项（自动读取 test_data/fms_0.mp4 ~ fms_4.mp4）")
    parser.add_argument("--test-dir", type=str, default="test_data",
                        help="--test-all 时读取的视频目录 (默认: test_data)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="输出标注视频路径")
    parser.add_argument("--json", "-j", type=str, default=None,
                        help="输出 JSON 结果路径")
    parser.add_argument("--model", "-m", type=str, default="yolov8n-pose.pt",
                        help="YOLO-Pose 模型路径 (默认: yolov8n-pose.pt)")
    parser.add_argument("--device", "-d", type=str, default="auto",
                        help="推理设备: auto / cpu / cuda")
    parser.add_argument("--show", action="store_true",
                        help="实时显示处理画面")
    parser.add_argument("--skip", type=int, default=2,
                        help="跳帧检测间隔 (默认: 2，每 2 帧检测一次)")
    args = parser.parse_args()

    # ── 模式：--test-all ──
    if args.test_all:
        all_summaries = {}
        base_dir = args.test_dir
        for idx in range(5):
            video_path = os.path.join(base_dir, f"fms_{idx}.mp4")
            if not os.path.exists(video_path):
                print(f"  ⚠ 跳过测试 {idx}：{video_path} 不存在")
                continue
            out_path = os.path.join(base_dir, f"fms_{idx}_result.mp4")
            json_path = os.path.join(base_dir, f"fms_{idx}_result.json")
            print(f"\n{'#' * 60}")
            print(f"#  测试 {idx}/5: {FMS_TEST_NAMES[idx]}")
            print(f"{'#' * 60}")
            summary = process_video(
                input_path=video_path,
                output_path=out_path,
                output_json=json_path,
                model_path=args.model,
                device=args.device,
                show=args.show,
                skip_frames=args.skip,
                test_idx=idx,
            )
            all_summaries[idx] = summary

        # 汇总报告
        print(f"\n{'=' * 60}")
        print(f"  FMS 五项综合汇总")
        print(f"{'=' * 60}")
        total_score = 0
        count = 0
        for idx in range(5):
            s = all_summaries.get(idx)
            if s:
                sc = s.get("overall_score", "N/A")
                print(f"  {FMS_TEST_NAMES[idx]}: {sc} 分  [{s['risk_level']}]")
                if isinstance(sc, (int, float)):
                    total_score += sc
                    count += 1
            else:
                print(f"  {FMS_TEST_NAMES[idx]}: 未测试")
        if count > 0:
            avg = total_score / count
            print(f"  ---")
            print(f"  综合均分: {avg:.1f} 分")
        return

    # ── 模式：单项测试 ──
    if args.input is None:
        parser.error("请指定 --input 或使用 --test-all")

    input_stem = Path(args.input).stem
    if args.output is None:
        args.output = f"tests/output/{input_stem}_fms_result.mp4"
    if args.json is None:
        args.json = f"tests/output/{input_stem}_fms_result.json"

    process_video(
        input_path=args.input,
        output_path=args.output,
        output_json=args.json,
        model_path=args.model,
        device=args.device,
        show=args.show,
        skip_frames=args.skip,
        test_idx=args.test_idx,
    )


if __name__ == "__main__":
    main()
