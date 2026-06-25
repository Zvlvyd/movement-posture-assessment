from typing import List, Dict
from .scoring import FMSScore

class ProblemTagger:
    TAG_THRESHOLDS = {
        'balance': [
            {'name': '平衡能力差', 'threshold': 40, 'description': '闭眼单腿站立时间不足'},
            {'name': '平衡能力不足', 'threshold': 60, 'description': '闭眼单腿站立时间偏短'},
        ],
        'flexibility': [
            {'name': '下肢灵活性差', 'threshold': 40, 'description': '深蹲深度严重不足'},
            {'name': '下肢灵活性不足', 'threshold': 60, 'description': '深蹲深度偏浅'},
        ],
        'upper_limb': [
            {'name': '肩关节活动受限', 'threshold': 40, 'description': '双手背后距离过大'},
            {'name': '肩关节活动不足', 'threshold': 60, 'description': '双手背后距离偏大'},
        ],
        'core': [
            {'name': '核心力量弱', 'threshold': 40, 'description': '平板支撑时间严重不足'},
            {'name': '核心力量不足', 'threshold': 60, 'description': '平板支撑时间偏短'},
        ],
        'symmetry': [
            {'name': '双侧严重不对称', 'threshold': 40, 'description': '左右两侧动作质量差异大'},
            {'name': '双侧不对称', 'threshold': 60, 'description': '左右两侧存在差异'},
        ],
    }
    
    @classmethod
    def tag(cls, scores: List[FMSScore]) -> List[Dict]:
        tags = []
        for s in scores:
            if s.dimension in cls.TAG_THRESHOLDS:
                for rule in cls.TAG_THRESHOLDS[s.dimension]:
                    if s.score < rule['threshold']:
                        tags.append({
                            'name': rule['name'],
                            'dimension': s.dimension,
                            'description': rule['description'],
                            'score': round(s.score, 1),
                        })
                        break
        return tags
