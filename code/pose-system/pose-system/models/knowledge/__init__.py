"""
Knowledge base — typed accessors for reference data (exercises, muscles,
problems, ROM norms, thresholds).

Usage:
    from models.knowledge import KnowledgeBase
    kb = KnowledgeBase()
    ex = kb.get_exercise("squat")
"""
from .loader import KnowledgeBase

__all__ = ["KnowledgeBase"]
