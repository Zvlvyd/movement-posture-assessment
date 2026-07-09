# -*- coding: utf-8 -*-
"""
Fusion Engine
Combines static findings, ROM-vs-norms validation, and velocity asymmetry
detection into final confidence scores. Confirms / rejects / adjusts each
static finding based on dynamic evidence.

Weighting: static × 0.3 + ROM × 0.3 + velocity × 0.4
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .velocity_analyzer import VelocityAsymmetryFinding


@dataclass
class FindingValidation:
    """Validation result for a single static finding."""
    problem_flag: str                          # e.g. "shoulder_imbalance"
    problem_name: str                          # Chinese display name
    static_severity: str                       # original static severity
    static_confidence: float                   # 0.0-1.0 from static alone
    rom_score: float                           # 0.0-1.0 from ROM vs norms
    velocity_score: float                      # 0.0-1.0 from velocity analysis
    final_confidence: float                    # weighted fusion score
    verdict: str                               # "confirmed" | "rejected" | "adjusted" | "unverified"
    adjusted_severity: str                     # post-validation severity level
    velocity_findings: List[VelocityAsymmetryFinding] = field(default_factory=list)
    rom_details: Dict = field(default_factory=dict)
    explanation: str = ""


@dataclass
class FusionResult:
    """Complete fusion assessment result."""
    validations: List[FindingValidation]
    overall_static_score: float
    overall_rom_score: float
    overall_velocity_score: float
    fused_overall_score: float
    confirmed_count: int = 0
    rejected_count: int = 0
    adjusted_count: int = 0
    unverified_count: int = 0


class FusionEngine:
    """
    Fuses static + ROM + velocity evidence into final validated posture assessment.

    Algorithm per finding:
      static_score  = severity_map[severity]          (0.1 severe → 1.0 normal)
      rom_score     = _rom_score(ratios, joint)       (0.0-1.0, from ROM vs norms)
      velocity_score = severity_map[velocity_severity] (0.1 severe → 1.0 none)

      final = static_score * 0.3 + rom_score * 0.3 + velocity_score * 0.4

      < 0.3 → confirmed (both static and dynamic agree)
      > 0.7 → rejected  (static not corroborated by dynamic)
      else  → adjusted  (severity tempered by dynamic evidence)
    """

    WEIGHT_STATIC = 0.3
    WEIGHT_ROM = 0.3
    WEIGHT_VELOCITY = 0.4

    # Severity → confidence score mapping (higher = more normal/better)
    SEVERITY_SCORE = {
        "severe": 0.1,
        "moderate": 0.35,
        "mild": 0.65,
        "normal": 1.0,
    }

    # Reverse mapping for adjusted_severity
    SCORE_REVERSE = [
        (0.0, "severe"),
        (0.3, "moderate"),
        (0.6, "mild"),
        (0.85, "normal"),
    ]

    # Severity downgrade by one level
    SEVERITY_DOWNGRADE = {
        "severe": "moderate",
        "moderate": "mild",
        "mild": "normal",
        "normal": "normal",
    }

    # Severity upgrade by one level
    SEVERITY_UPGRADE = {
        "normal": "mild",
        "mild": "moderate",
        "moderate": "severe",
        "severe": "severe",
    }

    def __init__(self, w_static: float = None, w_rom: float = None,
                 w_velocity: float = None):
        if w_static is not None:
            self.WEIGHT_STATIC = w_static
        if w_rom is not None:
            self.WEIGHT_ROM = w_rom
        if w_velocity is not None:
            self.WEIGHT_VELOCITY = w_velocity

    def fuse(self, static_findings: List,
             rom_ratios: Dict[str, float] = None,
             velocity_findings: List[VelocityAsymmetryFinding] = None,
             problem_to_rom_joints: Dict[str, List[str]] = None) -> FusionResult:
        """
        Fuse all evidence sources for each static finding.

        Args:
            static_findings: list of StaticFinding objects (from MultiViewAnalyzer)
            rom_ratios: {angle_key: ratio} where ratio = measured_ROM / norm_min
            velocity_findings: list of VelocityAsymmetryFinding
            problem_to_rom_joints: {flag: [relevant angle_keys]} for ROM lookup

        Returns:
            FusionResult with validated findings.
        """
        rom_ratios = rom_ratios or {}
        velocity_findings = velocity_findings or []
        problem_to_rom_joints = problem_to_rom_joints or PROBLEM_ROM_JOINTS

        # Index velocity findings by joint
        velocity_by_joint: Dict[str, List[VelocityAsymmetryFinding]] = {}
        for vf in velocity_findings:
            joint = vf.joint
            if joint not in velocity_by_joint:
                velocity_by_joint[joint] = []
            velocity_by_joint[joint].append(vf)

        validations = []
        for sf in static_findings:
            validation = self._validate_finding(
                sf, rom_ratios, velocity_by_joint, problem_to_rom_joints
            )
            validations.append(validation)

        # Compute overall scores
        if validations:
            static_scores = [v.static_confidence for v in validations]
            rom_scores = [v.rom_score for v in validations]
            vel_scores = [v.velocity_score for v in validations]

            overall_static = sum(static_scores) / len(static_scores)
            overall_rom = sum(rom_scores) / len(rom_scores)
            overall_velocity = sum(vel_scores) / len(vel_scores)

            fused_overall = (
                overall_static * self.WEIGHT_STATIC +
                overall_rom * self.WEIGHT_ROM +
                overall_velocity * self.WEIGHT_VELOCITY
            )
        else:
            overall_static = overall_rom = overall_velocity = 1.0
            fused_overall = 1.0

        return FusionResult(
            validations=validations,
            overall_static_score=round(overall_static, 3),
            overall_rom_score=round(overall_rom, 3),
            overall_velocity_score=round(overall_velocity, 3),
            fused_overall_score=round(fused_overall * 100, 1),
            confirmed_count=sum(1 for v in validations if v.verdict == "confirmed"),
            rejected_count=sum(1 for v in validations if v.verdict == "rejected"),
            adjusted_count=sum(1 for v in validations if v.verdict == "adjusted"),
            unverified_count=sum(1 for v in validations if v.verdict == "unverified"),
        )

    def _validate_finding(self, sf, rom_ratios, velocity_by_joint,
                          problem_to_rom_joints) -> FindingValidation:
        """Validate a single static finding."""
        flag = sf.flag

        # possible_scoliosis is always unverified
        if flag == "possible_scoliosis":
            return FindingValidation(
                problem_flag=flag,
                problem_name=sf.name if hasattr(sf, 'name') else flag,
                static_severity=sf.severity if hasattr(sf, 'severity') else "normal",
                static_confidence=0.5,
                rom_score=0.5,
                velocity_score=0.5,
                final_confidence=0.5,
                verdict="unverified",
                adjusted_severity=sf.severity if hasattr(sf, 'severity') else "normal",
                explanation="脊柱侧偏需专业X光评估确认，本系统不做运动验证。建议就医。",
            )

        # 1. Static evidence
        severity = sf.severity if hasattr(sf, 'severity') else "normal"
        static_score = self.SEVERITY_SCORE.get(severity, 0.5)

        # 2. ROM evidence
        relevant_joints = problem_to_rom_joints.get(flag, [])
        rom_scores_list = []
        rom_details = {}
        for joint_key in relevant_joints:
            if joint_key in rom_ratios:
                ratio = rom_ratios[joint_key]
                rom_scores_list.append(self._ratio_to_score(ratio))
                rom_details[joint_key] = {
                    "ratio": round(ratio, 2),
                    "score": round(self._ratio_to_score(ratio), 2),
                }
        rom_score = sum(rom_scores_list) / len(rom_scores_list) if rom_scores_list else 0.5

        # 3. Velocity evidence
        flag_velocity_findings = []
        # Map flag to relevant joint base names
        joint_bases = _flag_to_joint_bases(flag)
        for base in joint_bases:
            if base in velocity_by_joint:
                flag_velocity_findings.extend(velocity_by_joint[base])

        if flag_velocity_findings:
            # Take the worst (lowest score = worst severity) velocity finding
            worst_severity = "normal"
            for vf in flag_velocity_findings:
                sev_order = {"severe": 0, "moderate": 1, "mild": 2, "normal": 3}
                if sev_order.get(vf.severity, 3) < sev_order.get(worst_severity, 3):
                    worst_severity = vf.severity
            velocity_score = self.SEVERITY_SCORE.get(worst_severity, 1.0)
        else:
            # No velocity pair for this problem → neutral
            velocity_score = 0.5

        # 4. Fusion
        final_confidence = (
            static_score * self.WEIGHT_STATIC +
            rom_score * self.WEIGHT_ROM +
            velocity_score * self.WEIGHT_VELOCITY
        )

        # 5. Verdict
        if final_confidence < 0.3:
            verdict = "confirmed"
            adjusted_severity = severity
        elif final_confidence > 0.7:
            verdict = "rejected"
            adjusted_severity = "normal"
        else:
            verdict = "adjusted"
            adjusted_severity = self._downgrade_severity(severity)

        # 6. Explanation
        explanation = self._build_explanation(
            flag, severity, static_score, rom_score, velocity_score,
            final_confidence, verdict, adjusted_severity, rom_details,
            flag_velocity_findings,
        )

        return FindingValidation(
            problem_flag=flag,
            problem_name=sf.name if hasattr(sf, 'name') else flag,
            static_severity=severity,
            static_confidence=round(static_score, 2),
            rom_score=round(rom_score, 2),
            velocity_score=round(velocity_score, 2),
            final_confidence=round(final_confidence, 2),
            verdict=verdict,
            adjusted_severity=adjusted_severity,
            velocity_findings=flag_velocity_findings,
            rom_details=rom_details,
            explanation=explanation,
        )

    def _ratio_to_score(self, ratio: float) -> float:
        """Convert ROM ratio to 0-1 score (same logic as UnifiedScoringEngine)."""
        if ratio >= 1.0:
            return 1.0
        elif ratio >= 0.8:
            return 0.8 + (ratio - 0.8) / 0.2 * 0.2
        elif ratio >= 0.6:
            return 0.5 + (ratio - 0.6) / 0.2 * 0.3
        else:
            return max(0.0, ratio / 0.6 * 0.5)

    def _downgrade_severity(self, severity: str) -> str:
        return self.SEVERITY_DOWNGRADE.get(severity, severity)

    def _build_explanation(self, flag, severity, static, rom, vel, final,
                           verdict, adjusted, rom_details, vel_findings):
        """Generate Chinese explanation for the validation result."""
        flag_names = {
            "head_forward_posture": "头前倾",
            "shoulder_imbalance": "肩膀不对称",
            "pelvic_anterior_tilt": "骨盆前倾",
            "pelvic_lateral_tilt": "骨盆侧倾",
            "knee_hyperextension": "膝关节超伸",
            "pelvic_posterior_tilt": "骨盆后倾",
            "possible_scoliosis": "脊柱侧偏",
        }
        name = flag_names.get(flag, flag)
        verdict_cn = {"confirmed": "已确认", "rejected": "已排除", "adjusted": "已调整"}

        parts = [f"【{name}】静态分析({severity})"]
        if rom_details:
            parts.append(f"ROM检查{rom_details}")
        if vel_findings:
            parts.append(f"速度不对称({len(vel_findings)}处)")
        parts.append(f"→ 综合置信度{final:.2f}")
        parts.append(f"→ {verdict_cn.get(verdict, verdict)}")
        if verdict == "adjusted":
            parts.append(f"→ 严重度调整为{adjusted}")

        return "；".join(parts)


# ----------------------------------------------------------------
# Flag → relevant ROM joint mapping (for ROM evidence lookup)
# ----------------------------------------------------------------
PROBLEM_ROM_JOINTS: Dict[str, List[str]] = {
    "head_forward_posture": ["neck_tilt", "head_forward_deg"],
    "shoulder_imbalance": ["left_shoulder", "right_shoulder"],
    "pelvic_anterior_tilt": ["left_hip", "right_hip", "trunk_tilt"],
    "pelvic_lateral_tilt": ["left_knee", "right_knee", "left_hip", "right_hip"],
    "knee_hyperextension": ["left_knee", "right_knee", "knee_hyperextension_deg"],
    "pelvic_posterior_tilt": ["left_hip", "right_hip", "trunk_tilt"],
    "possible_scoliosis": [],
}


def _flag_to_joint_bases(flag: str) -> List[str]:
    """Map problem flag to joint base names for velocity finding lookup."""
    mapping = {
        "shoulder_imbalance": ["shoulder"],
        "pelvic_lateral_tilt": ["knee", "hip"],
        "pelvic_anterior_tilt": ["hip"],
        "knee_hyperextension": ["knee"],
    }
    return mapping.get(flag, [])
