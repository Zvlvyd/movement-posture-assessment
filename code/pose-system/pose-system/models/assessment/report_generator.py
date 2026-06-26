# -*- coding: utf-8 -*-
"""
统一报告生成器 - 整合姿态分析、ROM追踪、不对称分析、评分结果
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .scoring import DimensionScore, UnifiedScoringEngine


@dataclass
class UnifiedAssessmentReport:
    """统一评估报告"""
    # 评分部分
    overall_score: float
    risk_level: str
    dimensions: List[Dict]
    
    # 雷达图数据
    chart_data: Dict
    
    # 体态问题（来自 PostureAnalyzer）
    posture_problems: List[Dict] = field(default_factory=list)
    
    # ROM 分析
    rom_analysis: List[Dict] = field(default_factory=list)
    
    # 不对称发现
    asymmetry_findings: List[Dict] = field(default_factory=list)
    
    # 肌肉级别分析
    muscle_analysis: Dict = field(default_factory=dict)
    
    # 训练处方
    exercise_plan: Dict = field(default_factory=dict)
    
    # 汇总文字
    summary: str = ""
    suggestions: List[str] = field(default_factory=list)


class ReportGenerator:
    """统一报告生成器"""
    
    @staticmethod
    def generate(
        scores: List[DimensionScore],
        overall: float,
        risk_level: str,
        posture_problems: List[Dict],
        movement_results: List,
        asymmetry_findings: List,
        exercise_plan: Optional[Dict] = None,
    ) -> UnifiedAssessmentReport:
        """生成完整评估报告"""
        
        # 维度数据
        dimensions = [
            {
                'key': s.dimension,
                'label': s.label,
                'score': s.score,
                'max': s.max_score,
                'details': s.details,
            }
            for s in scores
        ]
        
        # 雷达图数据
        chart_data = {
            'labels': [s.label for s in scores],
            'values': [s.score for s in scores],
            'max_values': [100.0] * len(scores),
        }
        
        # ROM 分析摘要
        rom_analysis = ReportGenerator._build_rom_analysis(movement_results)
        
        # 不对称发现
        asym_data = ReportGenerator._build_asymmetry_data(asymmetry_findings)
        
        # 肌肉分析
        muscle_analysis = ReportGenerator._build_muscle_analysis(posture_problems)
        
        # 汇总
        summary = ReportGenerator._generate_summary(overall, risk_level, posture_problems, asymmetry_findings)
        suggestions = ReportGenerator._generate_suggestions(scores, posture_problems)
        
        return UnifiedAssessmentReport(
            overall_score=overall,
            risk_level=risk_level,
            dimensions=dimensions,
            chart_data=chart_data,
            posture_problems=posture_problems,
            rom_analysis=rom_analysis,
            asymmetry_findings=asym_data,
            muscle_analysis=muscle_analysis,
            exercise_plan=exercise_plan or {},
            summary=summary,
            suggestions=suggestions,
        )
    
    @staticmethod
    def _build_rom_analysis(movement_results: List) -> List[Dict]:
        """构建 ROM 分析摘要"""
        rom_items = []
        for result in movement_results:
            for rom in getattr(result, 'joint_roms', []):
                rom_items.append({
                    'movement': getattr(result, 'movement_name', ''),
                    'joint': rom.joint,
                    'side': rom.side,
                    'rom_deg': rom.rom_deg,
                    'peak_angle': rom.peak_angle,
                    'min_angle': rom.min_angle,
                    'plateau_detected': rom.plateau_detected,
                    'confidence': rom.confidence,
                })
        return rom_items
    
    @staticmethod
    def _build_asymmetry_data(findings: List) -> List[Dict]:
        """构建不对称数据"""
        data = []
        for f in findings:
            data.append({
                'joint': getattr(f, 'joint', ''),
                'side_limited': getattr(f, 'side_limited', ''),
                'rom_left': getattr(f, 'rom_left', 0),
                'rom_right': getattr(f, 'rom_right', 0),
                'diff_pct': getattr(f, 'diff_pct', 0),
                'severity': getattr(f, 'severity', ''),
                'related_muscles_tight': getattr(f, 'related_muscles_tight', []),
                'related_muscles_weak': getattr(f, 'related_muscles_weak', []),
            })
        return data
    
    @staticmethod
    def _build_muscle_analysis(posture_problems: List[Dict]) -> Dict:
        """从体态问题中提取肌肉级别分析"""
        tight_muscles = []
        weak_muscles = []
        
        for problem in posture_problems:
            severity = problem.get('severity', 'mild')
            for m in problem.get('tight_muscles', []):
                tight_muscles.append({
                    'name': m.get('name', ''),
                    'en': m.get('en', ''),
                    'desc': m.get('desc', ''),
                    'related_problem': problem.get('name', ''),
                    'severity': severity,
                })
            for m in problem.get('weak_muscles', []):
                weak_muscles.append({
                    'name': m.get('name', ''),
                    'en': m.get('en', ''),
                    'desc': m.get('desc', ''),
                    'related_problem': problem.get('name', ''),
                    'severity': severity,
                })
        
        return {
            'tight_muscles': tight_muscles,
            'weak_muscles': weak_muscles,
            'tight_count': len(tight_muscles),
            'weak_count': len(weak_muscles),
        }
    
    @staticmethod
    def _generate_summary(overall: float, risk_level: str,
                          posture_problems: List[Dict],
                          asymmetry_findings: List) -> str:
        """生成自然语言汇总"""
        parts = []
        
        severe_count = sum(1 for p in posture_problems if p.get('severity') == 'severe')
        moderate_count = sum(1 for p in posture_problems if p.get('severity') == 'moderate')
        asym_count = len(asymmetry_findings)
        
        if risk_level == 'high':
            parts.append(f'综合评分{overall}分，处于高风险状态。')
        elif risk_level == 'medium':
            parts.append(f'综合评分{overall}分，处于中等水平。')
        else:
            parts.append(f'综合评分{overall}分，运动功能良好。')
        
        if severe_count > 0:
            names = [p['name'] for p in posture_problems if p.get('severity') == 'severe']
            parts.append(f'检测到{severe_count}项严重体态问题：{"、".join(names)}，建议优先关注。')
        if moderate_count > 0:
            names = [p['name'] for p in posture_problems if p.get('severity') == 'moderate']
            parts.append(f'存在{moderate_count}项中度体态偏差：{"、".join(names)}。')
        if asym_count > 0:
            parts.append(f'发现{asym_count}项关节活动不对称。')
        
        if not parts:
            parts.append('各项体态评估指标在正常范围内。')
        
        return '。'.join(parts) + '。'
    
    @staticmethod
    def _generate_suggestions(scores: List[DimensionScore],
                              posture_problems: List[Dict]) -> List[str]:
        """生成训练建议"""
        suggestions = []
        
        for s in scores:
            if s.score < 40:
                suggestions.append(f'【{s.label}】严重不足（{s.score}分），需要重点训练')
            elif s.score < 60:
                suggestions.append(f'【{s.label}】较弱（{s.score}分），建议加强')
            elif s.score < 80:
                suggestions.append(f'【{s.label}】中等（{s.score}分），可继续提升')
        
        # 从体态问题提取建议
        for p in posture_problems:
            if p.get('severity') in ('severe', 'moderate'):
                note = p.get('note', '')
                if note:
                    suggestions.append(f'关于{p.get("name", "")}：{note}')
        
        if not suggestions:
            suggestions.append('各项能力均衡，继续保持当前训练习惯！')
        
        return suggestions