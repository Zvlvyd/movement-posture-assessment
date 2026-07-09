# -*- coding: utf-8 -*-
"""
Velocity Asymmetry Analyzer
Compares angular velocity (dθ/dt) between left and right joints
to detect rate-of-change asymmetry during movement.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math


@dataclass
class VelocityProfile:
    """Velocity profile for a single joint."""
    angle_key: str               # e.g. "left_knee"
    side: str                    # "left" | "right" | "bilateral"
    velocities: List[float] = field(default_factory=list)       # deg/frame
    timestamps: List[float] = field(default_factory=list)       # frame indices
    peak_velocity: float = 0.0
    avg_velocity: float = 0.0
    peak_frame: int = 0


@dataclass
class VelocityAsymmetryFinding:
    """Result of velocity asymmetry detection between a left-right joint pair."""
    joint: str                              # base joint name, e.g. "knee"
    left_angle_key: str                     # e.g. "left_knee"
    right_angle_key: str                    # e.g. "right_knee"
    max_velocity_diff_pct: float            # peak frame-by-frame difference %
    sustained_region_start: int             # frame index where sustained excess began
    sustained_region_end: int               # frame index where it ended
    duration_frames: int                    # how many consecutive frames
    severity: str                           # "moderate" | "severe"
    left_profile: Optional[VelocityProfile] = None
    right_profile: Optional[VelocityProfile] = None
    detail: str = ""


class VelocityAnalyzer:
    """
    Detects left-right angular velocity asymmetry.

    Algorithm:
    1. Compute velocity via central difference: v[i] = (angle[i+1] - angle[i-1]) / 2
    2. Smooth with 3-frame rolling average
    3. Compute frame-by-frame velocity diff %: |vL - vR| / max(|vL|, |vR|) * 100
    4. Find contiguous regions where diff% > threshold AND speed > noise floor
    5. If any region spans >= SUSTAINED_FRAMES, flag it
    """

    # User-confirmed parameters
    VELOCITY_DIFF_THRESHOLD = 20.0      # percent
    SUSTAINED_FRAME_COUNT = 15          # 0.5s at 30fps
    MIN_PEAK_VELOCITY = 0.5             # deg/frame noise floor
    SEVERE_FRAME_COUNT = 25             # severe threshold

    def __init__(self, diff_threshold: float = None,
                 sustained_frames: int = None,
                 min_velocity: float = None):
        if diff_threshold is not None:
            self.VELOCITY_DIFF_THRESHOLD = diff_threshold
        if sustained_frames is not None:
            self.SUSTAINED_FRAME_COUNT = sustained_frames
        if min_velocity is not None:
            self.MIN_PEAK_VELOCITY = min_velocity

    def compute_velocities(self, trajectory: List[float]) -> List[float]:
        """
        Compute angular velocity from angle trajectory.
        Uses central difference: v[i] = (a[i+1] - a[i-1]) / 2
        With forward/backward difference at endpoints.
        Returns smoothed velocity array (same length as input).
        """
        n = len(trajectory)
        if n < 3:
            return [0.0] * n

        v = [0.0] * n
        # Forward difference for first point
        v[0] = trajectory[1] - trajectory[0]
        # Central difference for interior points
        for i in range(1, n - 1):
            v[i] = (trajectory[i + 1] - trajectory[i - 1]) / 2.0
        # Backward difference for last point
        v[-1] = trajectory[-1] - trajectory[-2]

        # 3-frame rolling average smoothing
        if n >= 5:
            smoothed = [0.0] * n
            smoothed[0] = v[0]
            smoothed[-1] = v[-1]
            for i in range(1, n - 1):
                smoothed[i] = (v[i - 1] + v[i] + v[i + 1]) / 3.0
            return smoothed

        return v

    def build_velocity_profile(self, angle_key: str, side: str,
                               trajectory: List[float]) -> VelocityProfile:
        """Build a VelocityProfile from a raw angle trajectory."""
        velocities = self.compute_velocities(trajectory)
        if not velocities:
            return VelocityProfile(angle_key=angle_key, side=side)

        abs_vals = [abs(v) for v in velocities]
        peak = max(abs_vals)
        peak_frame = abs_vals.index(peak) if peak > 0 else 0
        avg = sum(abs_vals) / len(abs_vals) if abs_vals else 0

        return VelocityProfile(
            angle_key=angle_key,
            side=side,
            velocities=velocities,
            timestamps=list(range(len(velocities))),
            peak_velocity=round(peak, 3),
            avg_velocity=round(avg, 3),
            peak_frame=peak_frame,
        )

    def compare_velocity(self, left_trajectory: List[float],
                         right_trajectory: List[float],
                         left_key: str = "left",
                         right_key: str = "right",
                         joint_name: str = "unknown") -> Optional[VelocityAsymmetryFinding]:
        """
        Compare angular velocity between left and right joint trajectories.

        Returns VelocityAsymmetryFinding if sustained asymmetry detected, else None.
        """
        n = min(len(left_trajectory), len(right_trajectory))
        if n < self.SUSTAINED_FRAME_COUNT:
            return None

        # Build profiles
        left_profile = self.build_velocity_profile(left_key, "left", left_trajectory[:n])
        right_profile = self.build_velocity_profile(right_key, "right", right_trajectory[:n])

        v_left = left_profile.velocities
        v_right = right_profile.velocities

        # Compute frame-by-frame velocity difference percentage
        diff_pcts = []
        exceed_frames = []
        for i in range(n):
            abs_l = abs(v_left[i])
            abs_r = abs(v_right[i])
            max_mag = max(abs_l, abs_r, 0.001)
            diff_pct = abs(v_left[i] - v_right[i]) / max_mag * 100.0
            diff_pcts.append(diff_pct)

            # Frame exceeds threshold AND at least one side has meaningful velocity
            if diff_pct > self.VELOCITY_DIFF_THRESHOLD and max(abs_l, abs_r) > self.MIN_PEAK_VELOCITY:
                exceed_frames.append(i)

        if not exceed_frames:
            return None

        # Find longest contiguous region
        regions = self._find_contiguous_regions(exceed_frames)
        if not regions:
            return None

        # Pick the longest region
        best_region = max(regions, key=lambda r: r[1] - r[0])
        start, end = best_region
        duration = end - start + 1

        if duration < self.SUSTAINED_FRAME_COUNT:
            return None

        # Severity classification
        if duration >= self.SEVERE_FRAME_COUNT:
            severity = "severe"
        else:
            severity = "moderate"

        # Max diff in this region
        max_diff_in_region = max(diff_pcts[start:end + 1])

        # Build detail message
        detail = (
            f"{joint_name}: 左右速度差最大{max_diff_in_region:.1f}%, "
            f"持续{duration}帧({duration / 30:.1f}秒), "
            f"范围: 帧{start}-{end}"
        )

        return VelocityAsymmetryFinding(
            joint=joint_name,
            left_angle_key=left_key,
            right_angle_key=right_key,
            max_velocity_diff_pct=round(max_diff_in_region, 1),
            sustained_region_start=start,
            sustained_region_end=end,
            duration_frames=duration,
            severity=severity,
            left_profile=left_profile,
            right_profile=right_profile,
            detail=detail,
        )

    def compare_velocity_realtime(self, v_left: List[float], v_right: List[float],
                                  window_size: int = 30) -> Optional[Dict]:
        """
        Real-time variant: checks the last `window_size` frames for sustained asymmetry.
        Returns alert dict if threshold exceeded, else None.
        """
        if len(v_left) < window_size or len(v_right) < window_size:
            return None

        recent_l = v_left[-window_size:]
        recent_r = v_right[-window_size:]

        n = len(recent_l)
        exceed_count = 0
        max_diff = 0.0
        for i in range(n):
            abs_l = abs(recent_l[i])
            abs_r = abs(recent_r[i])
            max_mag = max(abs_l, abs_r, 0.001)
            diff_pct = abs(recent_l[i] - recent_r[i]) / max_mag * 100.0
            if diff_pct > self.VELOCITY_DIFF_THRESHOLD and max(abs_l, abs_r) > self.MIN_PEAK_VELOCITY:
                exceed_count += 1
                max_diff = max(max_diff, diff_pct)
            else:
                exceed_count = 0

        if exceed_count >= self.SUSTAINED_FRAME_COUNT:
            return {
                "alert": True,
                "max_diff_pct": round(max_diff, 1),
                "duration_frames": exceed_count,
                "severity": "severe" if exceed_count >= self.SEVERE_FRAME_COUNT else "moderate",
            }

        return None

    def analyze_pairs(self, tracker, pairs: List[Tuple[str, str]],
                      joint_names: List[str] = None) -> List[VelocityAsymmetryFinding]:
        """
        Analyze multiple left-right joint pairs using a ROMTracker instance.

        Args:
            tracker: ROMTracker instance with accumulated angle data
            pairs: list of (left_angle_key, right_angle_key) tuples
            joint_names: optional display names for each pair

        Returns list of VelocityAsymmetryFinding for pairs with asymmetry.
        """
        if joint_names is None:
            joint_names = [p[0].replace("left_", "").replace("right_", "") for p in pairs]

        findings = []
        for i, (left_key, right_key) in enumerate(pairs):
            left_hist = tracker.get_angle_history(left_key)
            right_hist = tracker.get_angle_history(right_key)

            if not left_hist or not right_hist:
                continue

            joint_name = joint_names[i] if i < len(joint_names) else left_key
            finding = self.compare_velocity(
                left_hist, right_hist,
                left_key=left_key, right_key=right_key,
                joint_name=joint_name,
            )
            if finding:
                findings.append(finding)

        return findings

    @staticmethod
    def _find_contiguous_regions(indices: List[int]) -> List[Tuple[int, int]]:
        """Group consecutive frame indices into (start, end) regions."""
        if not indices:
            return []
        regions = []
        start = indices[0]
        prev = indices[0]
        for i in indices[1:]:
            if i == prev + 1:
                prev = i
            else:
                regions.append((start, prev))
                start = i
                prev = i
        regions.append((start, prev))
        return regions
