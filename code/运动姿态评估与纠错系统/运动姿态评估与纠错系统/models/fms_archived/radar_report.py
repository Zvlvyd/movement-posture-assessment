from typing import List, Dict
from .scoring import FMSScore

class RadarReport:
    @staticmethod
    def generate(scores: List[FMSScore], overall: float, risk_level: str) -> Dict:
        return {
            'overall_score': overall,
            'risk_level': risk_level,
            'dimensions': [
                {
                    'key': s.dimension,
                    'label': s.label,
                    'score': round(s.score, 1),
                    'max': 100.0,
                }
                for s in scores
            ],
            'chart_data': {
                'labels': [s.label for s in scores],
                'values': [round(s.score, 1) for s in scores],
                'max_values': [100.0] * len(scores),
            },
            'suggestions': RadarReport._generate_suggestions(scores),
            'summary': RadarReport._generate_summary(overall, risk_level, scores),
        }
    
    @staticmethod
    def _generate_suggestions(scores: List[FMSScore]) -> List[str]:
        suggestions = []
        for s in scores:
            if s.score < 40:
                suggestions.append(f'{s.label}严重不足，需要重点训练')
            elif s.score < 60:
                suggestions.append(f'{s.label}较弱，建议加强')
            elif s.score < 80:
                suggestions.append(f'{s.label}中等，可继续提升')
        if not suggestions:
            suggestions.append('各项能力均衡，继续保持！')
        return suggestions
    
    @staticmethod
    def _generate_summary(overall: float, risk_level: str, scores: List[FMSScore]) -> str:
        if risk_level == 'high':
            return f'综合评分{overall}分，处于高风险状态。建议立即开始针对性矫正训练。'
        elif risk_level == 'medium':
            return f'综合评分{overall}分，处于中等水平。部分动作能力有待提升。'
        else:
            return f'综合评分{overall}分，运动功能良好。可进入进阶训练阶段。'
