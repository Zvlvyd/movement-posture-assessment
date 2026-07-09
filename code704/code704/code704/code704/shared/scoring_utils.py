# -*- coding: utf-8 -*-
"""
Shared scoring utilities — single source of truth for dimension score computation
and flag-to-dimension mappings, used by both assessment_service and multi_view_assessment.
"""

# Flag → dimension mapping (which dimension each problem flag affects)
flag_to_dimension: dict = {
    "shoulder_imbalance": "symmetry",
    "pelvic_lateral_tilt": "symmetry",
    "head_forward_posture": "upper_limb",
    "knee_hyperextension": "flexibility",
    "pelvic_anterior_tilt": "core",
    "pelvic_posterior_tilt": "core",
    "possible_scoliosis": "symmetry",
}

# Severity → penalty points (deducted from 100 for each dimension)
severity_penalty_map: dict = {
    "severe": 30,
    "moderate": 20,
    "mild": 10,
    "normal": 0,
}

# 5 assessment dimensions with labels
DIMENSIONS: list = [
    ("balance", "平衡"),
    ("flexibility", "灵活性"),
    ("upper_limb", "上肢"),
    ("core", "核心"),
    ("symmetry", "对称性"),
]


def compute_dimension_scores(fusion_result) -> dict:
    """
    Compute 5-dimension scores from validated fusion results.

    Args:
        fusion_result: FusionResult with .validations list of FindingValidation objects.
                       Each has .verdict ("confirmed"/"rejected"/"adjusted")
                       and .adjusted_severity ("severe"/"moderate"/"mild"/"normal")

    Returns:
        dict of {dimension_key: score_0_to_100}
    """
    penalties = {d: 0 for d in ["balance", "flexibility", "upper_limb", "core", "symmetry"]}

    for v in fusion_result.validations:
        if v.verdict == "rejected":
            continue  # Excluded — static finding not corroborated by dynamic
        dim = flag_to_dimension.get(v.problem_flag)
        if dim is None:
            continue
        penalties[dim] += severity_penalty_map.get(v.adjusted_severity, 0)

    return {d: max(0, 100 - p) for d, p in penalties.items()}
