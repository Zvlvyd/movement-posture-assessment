# -*- coding: utf-8 -*-
"""
Multi-View Posture Analyzer
Accepts keypoints from 3 views (front/back/side), delegates to PostureAnalyzer
per-view methods, merges findings with weighted confidence.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np

from models.posture_analyzer import PostureAnalyzer


@dataclass
class ViewKeypoints:
    """Keypoints from a single view photo."""
    view: str                    # "front" | "back" | "side"
    keypoints: List[List[float]] # (17, 2) or (17, 3) list


@dataclass
class StaticFinding:
    """A single static posture finding with per-view evidence."""
    flag: str                    # e.g. "shoulder_imbalance"
    name: str                    # Chinese display name
    severity: str                # "severe" | "moderate" | "mild" | "normal"
    value: float                 # merged measurement value
    unit: str                    # "px" | "°"
    normal_range: str            # e.g. "< 10 px"
    source_views: List[str] = field(default_factory=list)  # which views contributed
    measurement_details: Dict[str, float] = field(default_factory=dict)  # per-view values


@dataclass
class MergedPostureFindings:
    """Complete merged posture analysis from multi-view photos."""
    measurements: Dict[str, float]        # merged measurements
    flags: List[str]                      # all unique flags
    findings: List[StaticFinding]         # detailed findings with severity
    flag_sources: Dict[str, List[str]]    # per-view flag contributions
    summary: str = ""


class MultiViewAnalyzer:
    """
    Orchestrates multi-view posture analysis:
    1. Runs PostureAnalyzer on each view independently
    2. Merges measurements using weighted averaging
    3. Produces unified StaticFinding list with severity
    """

    def __init__(self):
        self.analyzer = PostureAnalyzer()

    def analyze(self, front_kps: Optional[List[List[float]]] = None,
                back_kps: Optional[List[List[float]]] = None,
                side_kps: Optional[List[List[float]]] = None) -> MergedPostureFindings:
        """
        Run multi-view analysis. At minimum, front view is required.
        Back and side are optional — missing views are skipped.
        """
        front_m = self.analyzer.analyze_front_view(front_kps) if front_kps else None
        back_m = self.analyzer.analyze_back_view(back_kps) if back_kps else None
        side_m = self.analyzer.analyze_side_view(side_kps) if side_kps else None

        # If only front available, return front-only result
        if front_m and not back_m and not side_m:
            return self._build_findings(front_m, {"front": front_m.get("flags", [])})

        # Default missing views to empty
        front_m = front_m or {"error": "missing"}
        back_m = back_m or {"error": "missing"}
        side_m = side_m or {"error": "missing"}

        # Merge via PostureAnalyzer
        merged = self.analyzer.merge_multiview_measurements(front_m, back_m, side_m)
        flag_sources = merged.pop("_flag_sources", {"front": [], "back": [], "side": []})

        return self._build_findings(merged, flag_sources)

    def _build_findings(self, measurements: Dict, flag_sources: Dict) -> MergedPostureFindings:
        """Build structured StaticFinding list from merged measurements."""
        findings = []
        flags = measurements.get("flags", [])

        for flag in flags:
            problem_def = self.analyzer.problems.get(flag, {})
            metric_key = problem_def.get("metric", "")
            value = measurements.get(metric_key, 0)
            severity = self.analyzer.severity_judge(value, metric_key)
            threshold = self.analyzer.thresholds.get(metric_key, {})

            # Determine which views found this flag
            sources = [
                view for view, view_flags in flag_sources.items()
                if flag in view_flags
            ]

            findings.append(StaticFinding(
                flag=flag,
                name=problem_def.get("name", flag),
                severity=severity,
                value=value,
                unit=threshold.get("unit", ""),
                normal_range=threshold.get("normal_desc", ""),
                source_views=sources if sources else ["unknown"],
                measurement_details={
                    k: measurements.get(k, 0)
                    for k in measurements if k not in ("flags", "error")
                },
            ))

        # Sort: severe first, then moderate, then mild
        severity_order = {"severe": 0, "moderate": 1, "mild": 2, "normal": 3}
        findings.sort(key=lambda f: severity_order.get(f.severity, 99))

        # Generate summary
        summary = self._summarize(findings)

        return MergedPostureFindings(
            measurements={k: v for k, v in measurements.items() if k not in ("flags", "error")},
            flags=flags,
            findings=findings,
            flag_sources=flag_sources,
            summary=summary,
        )

    def _summarize(self, findings: List[StaticFinding]) -> str:
        """Generate Chinese summary of findings."""
        severe = [f for f in findings if f.severity == "severe"]
        moderate = [f for f in findings if f.severity == "moderate"]
        mild = [f for f in findings if f.severity == "mild"]

        parts = []
        if severe:
            names = [f.name for f in severe]
            parts.append(f"检测到{len(severe)}项严重体态问题：{'、'.join(names)}")
        if moderate:
            names = [f.name for f in moderate]
            parts.append(f"存在{len(moderate)}项中度体态偏差：{'、'.join(names)}")
        if mild:
            names = [f.name for f in mild]
            parts.append(f"发现{len(mild)}项轻度不对称")

        if not parts:
            return "各项体态评估指标在正常范围内"

        return "；".join(parts) + "。"
