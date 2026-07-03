# -*- coding: utf-8 -*-
"""FMS Scoring Engine - 综合FMS评分引擎"""
import math
from typing import List, Dict, Optional


class Score:
    def __init__(self, dimension: str, score_val: float, detail: str = ""):
        self.dimension = dimension
        self.score = round(score_val, 1)
        self.detail = detail


class FMSScoringEngine:
    DIMENSION_WEIGHTS = {
        "balance": 0.2, "flexibility": 0.25, "upper_limb": 0.15,
        "core": 0.2, "symmetry": 0.2,
    }

    def score_balance(self, duration_sec: float, sway_amplitude: float = 0) -> Score:
        """平衡能力评分

        Args:
            duration_sec: 单腿站立持续时间（秒）
            sway_amplitude: 身体晃动幅度（像素，可选）
        """
        base_score = min(100, max(0, duration_sec / 60.0 * 100))
        if sway_amplitude > 0:
            sway_penalty = min(30, sway_amplitude * 2)
            base_score = max(0, base_score - sway_penalty)
        detail = f"单腿站立 {duration_sec:.1f}s"
        if sway_amplitude > 0:
            detail += f"，晃动幅度 {sway_amplitude:.0f}px"
        return Score("balance", base_score, detail)

    def score_flexibility(self, depth_cm: float, trunk_angle: float = 0,
                          arm_ratio: float = 0) -> Score:
        """灵活性评分

        Args:
            depth_cm: 体前屈深度（cm）
            trunk_angle: 躯干倾斜角度（°）
            arm_ratio: 手臂伸展比例
        """
        depth_score = min(50, max(0, depth_cm / 20.0 * 50))
        trunk_score = min(50, max(0, (1.0 - abs(trunk_angle) / 30.0) * 50))
        arm_score = min(20, max(0, arm_ratio * 20))
        s = min(100, depth_score + trunk_score + arm_score)
        detail = f"体前屈 {depth_cm:.1f}cm"
        if trunk_angle > 0:
            detail += f"，躯干倾斜 {trunk_angle:.0f}°"
        return Score("flexibility", s, detail)

    def score_upper_limb(self, distance_cm: float) -> Score:
        """上肢功能评分

        Args:
            distance_cm: 背后触肩距离（cm，越小越好）
        """
        s = min(100, max(0, (1.0 - distance_cm / 200.0) * 100))
        detail = f"背后双手距 {distance_cm:.1f}cm"
        return Score("upper_limb", s, detail)

    def score_core(self, duration_sec: float, hip_drop_angle: float = 0) -> Score:
        """核心力量评分

        Args:
            duration_sec: 平板支撑持续时间（秒）
            hip_drop_angle: 臀部下降角度（°，可选）
        """
        base_score = min(100, max(0, duration_sec / 90.0 * 100))
        if hip_drop_angle > 5:
            penalty = min(30, (hip_drop_angle - 5) * 3)
            base_score = max(0, base_score - penalty)
        detail = f"平板支撑 {duration_sec:.1f}s"
        if hip_drop_angle > 0:
            detail += f"，臀部下降 {hip_drop_angle:.0f}°"
        return Score("core", base_score, detail)

    def score_symmetry(self, left: float, right: float) -> Score:
        """对称性评分

        Args:
            left: 左侧测量值
            right: 右侧测量值
        """
        diff = abs(left - right)
        total = (left + right) / 2.0
        ratio = diff / max(total, 0.01)
        s = max(0, 100 - ratio * 100)
        detail = f"左右差 {diff:.1f}"
        return Score("symmetry", s, detail)

    def compute_overall(self, scores: List[Score]) -> float:
        """计算综合评分"""
        if not scores:
            return 50.0
        total = sum(s.score * self.DIMENSION_WEIGHTS.get(s.dimension, 0.2)
                    for s in scores)
        wsum = sum(self.DIMENSION_WEIGHTS.get(s.dimension, 0.2) for s in scores)
        return round(total / max(wsum, 0.01), 1)

    def get_risk_level(self, overall: float,
                       scores: Optional[List[Score]] = None) -> str:
        """获取风险等级"""
        if overall >= 80:
            return "低风险"
        if overall >= 60:
            return "中风险"
        if overall >= 40:
            return "高风险"
        return "极高风险"

    def get_recommendations(self, scores: List[Score]) -> List[str]:
        """根据评分生成训练建议"""
        recommendations: List[str] = []
        for s in scores:
            if s.score < 40:
                if s.dimension == "balance":
                    recommendations.append(
                        "平衡能力较差，建议增加单腿站立、瑜伽平衡体式训练")
                elif s.dimension == "flexibility":
                    recommendations.append(
                        "灵活性不足，建议增加动态拉伸和泡沫轴放松")
                elif s.dimension == "upper_limb":
                    recommendations.append(
                        "上肢功能受限，建议增加肩关节活动度训练")
                elif s.dimension == "core":
                    recommendations.append(
                        "核心力量薄弱，建议增加平板支撑、鸟狗式等核心训练")
                elif s.dimension == "symmetry":
                    recommendations.append(
                        "左右不对称明显，建议增加单侧训练纠正不平衡")
            elif s.score < 60:
                if s.dimension == "balance":
                    recommendations.append("平衡能力一般，建议定期进行平衡训练")
                elif s.dimension == "flexibility":
                    recommendations.append(
                        "灵活性有待提高，建议训练前后充分拉伸")
                elif s.dimension == "core":
                    recommendations.append(
                        "核心力量一般，建议增加核心训练频率")
        return recommendations