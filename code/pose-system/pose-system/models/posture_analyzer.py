# -*- coding: utf-8 -*-
"""
Posture Analyzer - Adapted from alcoholWipe/posture-assessment
Uses COCO 17 keypoints to assess posture deviations, muscle imbalances,
and generate corrective exercise recommendations.
"""
import json
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np

# COCO keypoint indices
NOSE = 0
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16

KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def calc_angle(a, b, c):
    """Calculate angle at point b formed by points a-b-c"""
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    mag = math.sqrt(ax**2 + ay**2) * math.sqrt(cx**2 + cy**2)
    if mag == 0:
        return 0.0
    return math.degrees(math.acos(max(-1.0, min(1.0, (ax * cx + ay * cy) / mag))))


def safe_kp(keypoints, idx):
    """Safely get keypoint, return [0,0] if not available"""
    if idx < len(keypoints) and keypoints[idx][0] > 0 and keypoints[idx][1] > 0:
        return list(keypoints[idx])
    return [0, 0]


class PostureAnalyzer:
    def __init__(self):
        self.problems = self._load_json("problems.json")
        self.muscles = self._load_json("muscles.json")
        self.exercises = self._load_json("exercises.json")
        self.thresholds = self._load_json("thresholds.json")

    def _load_json(self, filename):
        path = KNOWLEDGE_DIR / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def analyze_from_keypoints(self, keypoints_front, keypoints_side=None):
        """Backward-compatible wrapper — delegates to analyze_front_view."""
        return self.analyze_front_view(keypoints_front, keypoints_side)

    def analyze_front_view(self, keypoints, keypoints_side=None):
        """
        Analyze posture from front-view keypoints.
        Returns measurements dict with flags.
        """
        kp = keypoints
        if not kp or len(kp) < 17:
            return {"error": "insufficient keypoints"}

        l_sh = safe_kp(kp, LEFT_SHOULDER)
        r_sh = safe_kp(kp, RIGHT_SHOULDER)
        l_hip = safe_kp(kp, LEFT_HIP)
        r_hip = safe_kp(kp, RIGHT_HIP)
        nose = safe_kp(kp, NOSE)
        l_ear = safe_kp(kp, LEFT_EAR)
        r_ear = safe_kp(kp, RIGHT_EAR)
        l_knee = safe_kp(kp, LEFT_KNEE)
        r_knee = safe_kp(kp, RIGHT_KNEE)
        l_ankle = safe_kp(kp, LEFT_ANKLE)
        r_ankle = safe_kp(kp, RIGHT_ANKLE)

        sh_mid_x = (l_sh[0] + r_sh[0]) / 2 if l_sh[0] > 0 and r_sh[0] > 0 else 0
        sh_mid_y = (l_sh[1] + r_sh[1]) / 2 if l_sh[1] > 0 and r_sh[1] > 0 else 0
        hip_mid_x = (l_hip[0] + r_hip[0]) / 2 if l_hip[0] > 0 and r_hip[0] > 0 else 0

        # Front view measurements
        shoulder_height_diff = round(r_sh[1] - l_sh[1], 1) if r_sh[1] > 0 and l_sh[1] > 0 else 0
        hip_height_diff = round(r_hip[1] - l_hip[1], 1) if r_hip[1] > 0 and l_hip[1] > 0 else 0
        head_tilt = round(
            math.degrees(math.atan2(nose[0] - sh_mid_x, max(sh_mid_y * 0.15, 1))), 1
        ) if nose[0] > 0 and sh_mid_x > 0 else 0
        spine_lateral = round(sh_mid_x - hip_mid_x, 1) if sh_mid_x > 0 and hip_mid_x > 0 else 0

        # Side view measurements (estimated from front — low accuracy)
        ear = l_ear if l_ear[0] > 0 else r_ear
        sh_for_side = l_sh if l_sh[0] > 0 else r_sh
        head_forward = round(abs(sh_for_side[0] - ear[0]), 1) if ear[0] > 0 else 0
        head_forward_deg = round(
            math.degrees(math.atan2(sh_for_side[0] - ear[0], max(sh_mid_y * 0.2, 1))), 1
        ) if ear[0] > 0 and sh_for_side[0] > 0 else 0

        # Knee hyperextension (estimated from front — very low accuracy)
        knee_angle = 0
        if l_hip[0] > 0 and l_knee[0] > 0 and l_ankle[0] > 0:
            knee_angle = calc_angle(l_hip, l_knee, l_ankle)
        knee_hyper = round(knee_angle - 180, 1)

        # Pelvic tilt (estimated from front — low accuracy)
        pelvic_offset = round(hip_mid_x - sh_mid_x, 1) if hip_mid_x > 0 and sh_mid_x > 0 else 0

        measurements = {
            "shoulder_height_diff_px": abs(shoulder_height_diff),
            "hip_height_diff_px": abs(hip_height_diff),
            "head_tilt_deg": abs(head_tilt),
            "head_forward_deg": abs(head_forward_deg),
            "spine_lateral_deviation_px": abs(spine_lateral),
            "knee_hyperextension_deg": knee_hyper,
            "pelvic_forward_offset_px": pelvic_offset,
        }

        flags = []
        if abs(shoulder_height_diff) > 10:
            flags.append("shoulder_imbalance")
        if abs(hip_height_diff) > 10:
            flags.append("pelvic_lateral_tilt")
        if abs(spine_lateral) > 15:
            flags.append("possible_scoliosis")
        if abs(head_forward_deg) > 12:
            flags.append("head_forward_posture")
        if knee_hyper < -5:
            flags.append("knee_hyperextension")
        if pelvic_offset > 20:
            flags.append("pelvic_anterior_tilt")
        elif pelvic_offset < -20:
            flags.append("pelvic_posterior_tilt")

        measurements["flags"] = flags
        return measurements

    def analyze_back_view(self, keypoints):
        """
        Analyze posture from back-view keypoints.
        COCO keypoints visible from back: shoulders, hips, knees, ankles (all good);
        nose partially; ears not visible.
        Can measure: shoulder/hip height diff, spine lateral deviation.
        Cannot measure: head forward, knee hyperextension, pelvic anterior tilt.
        """
        kp = keypoints
        if not kp or len(kp) < 17:
            return {"error": "insufficient keypoints"}

        l_sh = safe_kp(kp, LEFT_SHOULDER)
        r_sh = safe_kp(kp, RIGHT_SHOULDER)
        l_hip = safe_kp(kp, LEFT_HIP)
        r_hip = safe_kp(kp, RIGHT_HIP)
        nose = safe_kp(kp, NOSE)

        sh_mid_x = (l_sh[0] + r_sh[0]) / 2 if l_sh[0] > 0 and r_sh[0] > 0 else 0
        sh_mid_y = (l_sh[1] + r_sh[1]) / 2 if l_sh[1] > 0 and r_sh[1] > 0 else 0
        hip_mid_x = (l_hip[0] + r_hip[0]) / 2 if l_hip[0] > 0 and r_hip[0] > 0 else 0

        shoulder_height_diff = round(r_sh[1] - l_sh[1], 1) if r_sh[1] > 0 and l_sh[1] > 0 else 0
        hip_height_diff = round(r_hip[1] - l_hip[1], 1) if r_hip[1] > 0 and l_hip[1] > 0 else 0
        spine_lateral = round(sh_mid_x - hip_mid_x, 1) if sh_mid_x > 0 and hip_mid_x > 0 else 0
        head_tilt = round(
            math.degrees(math.atan2(nose[0] - sh_mid_x, max(sh_mid_y * 0.15, 1))), 1
        ) if nose[0] > 0 and sh_mid_x > 0 else 0

        measurements = {
            "shoulder_height_diff_px": abs(shoulder_height_diff),
            "hip_height_diff_px": abs(hip_height_diff),
            "head_tilt_deg": abs(head_tilt),
            "head_forward_deg": 0,        # not measurable from back
            "spine_lateral_deviation_px": abs(spine_lateral),
            "knee_hyperextension_deg": 0,  # not measurable from back
            "pelvic_forward_offset_px": 0,  # not measurable from back
        }

        flags = []
        if abs(shoulder_height_diff) > 10:
            flags.append("shoulder_imbalance")
        if abs(hip_height_diff) > 10:
            flags.append("pelvic_lateral_tilt")
        if abs(spine_lateral) > 15:
            flags.append("possible_scoliosis")

        measurements["flags"] = flags
        return measurements

    def analyze_side_view(self, keypoints):
        """
        Analyze posture from side-view keypoints.
        Uses the visible-side keypoints (preferring higher-confidence side).
        Direct sagittal measurements (head forward, knee angle, pelvic tilt)
        are significantly more accurate than front-view estimates.
        """
        kp = keypoints
        if not kp or len(kp) < 17:
            return {"error": "insufficient keypoints"}

        # Pick visible side: use left if left shoulder has higher x (closer to camera),
        # otherwise use right. In a side photo, one side's keypoints will be more prominent.
        l_sh = safe_kp(kp, LEFT_SHOULDER)
        r_sh = safe_kp(kp, RIGHT_SHOULDER)

        # Determine which side is facing the camera based on x position
        # The side closer to the camera has more reliable depth info
        use_left = l_sh[0] > r_sh[0] if l_sh[0] > 0 and r_sh[0] > 0 else (l_sh[0] > 0)

        ear = safe_kp(kp, LEFT_EAR) if use_left else safe_kp(kp, RIGHT_EAR)
        sh = l_sh if use_left else r_sh
        hip = safe_kp(kp, LEFT_HIP) if use_left else safe_kp(kp, RIGHT_HIP)
        knee = safe_kp(kp, LEFT_KNEE) if use_left else safe_kp(kp, RIGHT_KNEE)
        ankle = safe_kp(kp, LEFT_ANKLE) if use_left else safe_kp(kp, RIGHT_ANKLE)

        sh_y = sh[1] if sh[1] > 0 else 0

        # Head forward angle: ear relative to shoulder in sagittal plane
        head_forward_deg = 0
        if ear[0] > 0 and sh[0] > 0 and sh_y > 0:
            head_forward_deg = round(
                math.degrees(math.atan2(sh[0] - ear[0], max(sh_y * 0.2, 1))), 1
            )

        # Knee hyperextension: direct sagittal measurement
        knee_hyper = 0
        if hip[0] > 0 and knee[0] > 0 and ankle[0] > 0:
            knee_angle = calc_angle(hip, knee, ankle)
            knee_hyper = round(knee_angle - 180, 1)

        # Pelvic anterior tilt: shoulder-hip sagittal offset
        pelvic_offset = 0
        if hip[0] > 0 and sh[0] > 0:
            pelvic_offset = round(hip[0] - sh[0], 1)

        # Pelvic tilt angle: shoulder-hip line relative to vertical
        pelvic_tilt_deg = 0
        if sh[0] > 0 and sh_y > 0 and hip[0] > 0 and hip[1] > 0:
            dx = hip[0] - sh[0]
            dy = hip[1] - sh[1]
            if dy > 0:
                pelvic_tilt_deg = round(math.degrees(math.atan2(dx, dy)), 1)

        measurements = {
            "shoulder_height_diff_px": 0,    # not measurable from side
            "hip_height_diff_px": 0,          # not measurable from side
            "head_tilt_deg": 0,               # not measurable from side
            "head_forward_deg": abs(head_forward_deg),
            "spine_lateral_deviation_px": 0,  # not measurable from side
            "knee_hyperextension_deg": knee_hyper,
            "pelvic_forward_offset_px": abs(pelvic_offset),
            "pelvic_tilt_deg": abs(pelvic_tilt_deg),
        }

        flags = []
        if abs(head_forward_deg) > 12:
            flags.append("head_forward_posture")
        if knee_hyper < -5:
            flags.append("knee_hyperextension")
        if pelvic_offset > 20:
            flags.append("pelvic_anterior_tilt")
        elif pelvic_offset < -20:
            flags.append("pelvic_posterior_tilt")

        measurements["flags"] = flags
        return measurements

    def merge_multiview_measurements(self, front, back, side):
        """
        Merge measurements from three views using weighted averaging.
        front/back/side: measurement dicts from respective analyze_*_view() calls.

        View weights per metric:
          shoulder_height_diff:  front=0.5, back=0.5, side=0
          hip_height_diff:       front=0.5, back=0.5, side=0
          spine_lateral:         front=0.4, back=0.6, side=0
          head_forward:          front=0.2, back=0,   side=0.8
          knee_hyperextension:   front=0,   back=0,   side=1.0
          pelvic_forward:        front=0.3, back=0,   side=0.7

        Returns merged measurements dict + combined flags.
        """
        def weighted_avg(values_and_weights):
            """[(value, weight), ...] -> weighted average"""
            total_w = sum(w for _, w in values_and_weights if w > 0)
            if total_w == 0:
                return 0
            return round(sum(v * w for v, w in values_and_weights if w > 0) / total_w, 1)

        metrics = {}

        # shoulder_height_diff_px: front + back
        metrics["shoulder_height_diff_px"] = weighted_avg([
            (front.get("shoulder_height_diff_px", 0), 0.5),
            (back.get("shoulder_height_diff_px", 0), 0.5),
        ])

        # hip_height_diff_px: front + back
        metrics["hip_height_diff_px"] = weighted_avg([
            (front.get("hip_height_diff_px", 0), 0.5),
            (back.get("hip_height_diff_px", 0), 0.5),
        ])

        # head_tilt_deg: front + back
        metrics["head_tilt_deg"] = weighted_avg([
            (front.get("head_tilt_deg", 0), 0.5),
            (back.get("head_tilt_deg", 0), 0.5),
        ])

        # head_forward_deg: side-dominant (direct measurement), front as weak corroboration
        metrics["head_forward_deg"] = weighted_avg([
            (front.get("head_forward_deg", 0), 0.2),
            (side.get("head_forward_deg", 0), 0.8),
        ])

        # spine_lateral_deviation_px: back-dominant (better spine line visibility)
        metrics["spine_lateral_deviation_px"] = weighted_avg([
            (front.get("spine_lateral_deviation_px", 0), 0.4),
            (back.get("spine_lateral_deviation_px", 0), 0.6),
        ])

        # knee_hyperextension_deg: side only (direct sagittal measurement)
        metrics["knee_hyperextension_deg"] = side.get("knee_hyperextension_deg", 0)

        # pelvic_forward_offset_px: side-dominant, front as weak corroboration
        metrics["pelvic_forward_offset_px"] = weighted_avg([
            (front.get("pelvic_forward_offset_px", 0), 0.3),
            (side.get("pelvic_forward_offset_px", 0), 0.7),
        ])

        # Preserve pelvic_tilt_deg from side view
        if "pelvic_tilt_deg" in side:
            metrics["pelvic_tilt_deg"] = side["pelvic_tilt_deg"]

        # Merge flags from all views
        all_flags = set()
        all_flags.update(front.get("flags", []))
        all_flags.update(back.get("flags", []))
        all_flags.update(side.get("flags", []))

        metrics["flags"] = list(all_flags)

        # Record per-view flag sources for traceability
        metrics["_flag_sources"] = {
            "front": front.get("flags", []),
            "back": back.get("flags", []),
            "side": side.get("flags", []),
        }

        return metrics

    def severity_judge(self, value, metric_key):
        """Judge severity based on thresholds"""
        t = self.thresholds.get(metric_key, {})
        if not t:
            return "normal"
        direction = t.get("direction", "higher_worse")
        mild = t.get("mild", 999)
        moderate = t.get("moderate", 999)
        severe = t.get("severe", 999)

        if direction == "higher_worse":
            abs_val = abs(value) if value else 0
            if abs_val < mild: return "normal"
            if abs_val < moderate: return "mild"
            if abs_val < severe: return "moderate"
            return "severe"
        else:  # lower_worse
            if value > mild: return "normal"
            if value > moderate: return "mild"
            if value > severe: return "moderate"
            return "severe"

    def generate_report(self, measurements, fms_scores=None):
        """
        Generate a comprehensive posture analysis report.
        Returns dict with: flags, problems[], summary, exercises[]
        """
        measurements = measurements or {}
        flags = measurements.get("flags", [])
        fms_scores = fms_scores or []

        problems = []
        for flag in flags:
            p = self.problems.get(flag, {})
            if not p:
                continue
            metric_key = p.get("metric", "")
            value = measurements.get(metric_key, 0)
            severity = self.severity_judge(value, metric_key)
            threshold = self.thresholds.get(metric_key, {})

            problem = {
                "flag": flag,
                "name": p.get("name", flag),
                "severity": severity,
                "value": value,
                "normal_range": threshold.get("normal_desc", ""),
                "unit": threshold.get("unit", ""),
                "cause": p.get("cause", ""),
                "tight_muscles": [],
                "weak_muscles": [],
                "note": p.get("note", ""),
                "exercises": [],
            }

            # Add muscle details
            for m_name in p.get("tight_muscles", []):
                muscle = self.muscles.get(m_name, {})
                problem["tight_muscles"].append({
                    "name": m_name,
                    "en": muscle.get("en", ""),
                    "desc": muscle.get("desc", ""),
                })
            for m_name in p.get("weak_muscles", []):
                muscle = self.muscles.get(m_name, {})
                problem["weak_muscles"].append({
                    "name": m_name,
                    "en": muscle.get("en", ""),
                    "desc": muscle.get("desc", ""),
                })

            # Add exercises
            ex = self.exercises.get(flag, {})
            problem["exercises"] = {
                "stretch": ex.get("stretch", []),
                "strength": ex.get("strength", []),
            }

            problems.append(problem)

        # Sort by severity
        severity_order = {"severe": 0, "moderate": 1, "mild": 2, "normal": 3}
        problems.sort(key=lambda x: severity_order.get(x["severity"], 99))

        # Generate summary
        summary = self._generate_summary(problems, fms_scores)

        return {
            "problems": problems,
            "summary": summary,
            "fms_scores": fms_scores,
        }

    def _generate_summary(self, problems, fms_scores):
        """Generate natural language summary"""
        parts = []
        severe_count = sum(1 for p in problems if p["severity"] == "severe")
        moderate_count = sum(1 for p in problems if p["severity"] == "moderate")
        mild_count = sum(1 for p in problems if p["severity"] == "mild")

        if severe_count > 0:
            severe_names = [p["name"] for p in problems if p["severity"] == "severe"]
            parts.append(f"检测到{severe_count}项严重体态问题：{'、'.join(severe_names)}，建议优先关注。")
        if moderate_count > 0:
            moderate_names = [p["name"] for p in problems if p["severity"] == "moderate"]
            parts.append(f"存在{moderate_count}项中度体态偏差：{'、'.join(moderate_names)}，建议纳入日常训练计划。")
        if mild_count > 0:
            mild_names = [p["name"] for p in problems if p["severity"] == "mild"]
            parts.append(f"发现{len(mild_names)}项轻度不对称，注意日常姿势纠正。")

        if not parts:
            parts.append("各项体态评估指标在正常范围内，请继续保持良好的运动习惯。")

        # Add FMS summary
        if fms_scores:
            low_scores = [s for s in fms_scores if s.get("score", 100) < 60]
            if low_scores:
                parts.append(f"FMS测试中{'、'.join(s['label'] for s in low_scores)}得分偏低，建议针对性加强。")

        return "。".join(parts) + "。"

    def generate_exercise_plan(self, problems):
        """Generate a prioritized exercise plan from problems"""
        stretch_plan = []
        strength_plan = []

        for problem in problems:
            if problem["flag"] == "possible_scoliosis":
                continue

            ex = problem.get("exercises", {})
            for stretch in ex.get("stretch", []):
                stretch_plan.append({
                    "for_problem": problem["name"],
                    "name": stretch.get("name", ""),
                    "steps": stretch.get("steps", []),
                    "sets": stretch.get("sets", ""),
                    "cues": stretch.get("cues", []),
                })
            for strength in ex.get("strength", []):
                strength_plan.append({
                    "for_problem": problem["name"],
                    "name": strength.get("name", ""),
                    "steps": strength.get("steps", []),
                    "sets": strength.get("sets", ""),
                    "cues": strength.get("cues", []),
                })

        return stretch_plan, strength_plan
