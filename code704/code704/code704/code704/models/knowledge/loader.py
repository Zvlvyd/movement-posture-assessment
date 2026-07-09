"""Type-safe accessor for knowledge base JSON files."""
import json
import os
from typing import Dict, List, Optional

_KB_DIR = os.path.dirname(os.path.abspath(__file__))


class KnowledgeBase:
    """Loads and provides typed access to knowledge base JSON data."""

    def __init__(self):
        self._cache: Dict[str, dict] = {}

    def _load(self, filename: str) -> dict:
        if filename not in self._cache:
            path = os.path.join(_KB_DIR, filename)
            if not os.path.isfile(path):
                raise FileNotFoundError(f"Knowledge base file not found: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                self._cache[filename] = json.load(f)
        return self._cache[filename]

    # ── Accessors ──────────────────────────────

    def get_exercise(self, name: str) -> Optional[dict]:
        """Get exercise definition by name."""
        data = self._load("exercises.json")
        return data.get(name)

    def get_exercises(self) -> dict:
        """Get all exercise definitions."""
        return self._load("exercises.json")

    def get_muscle(self, name: str) -> Optional[dict]:
        """Get muscle definition by name."""
        data = self._load("muscles.json")
        return data.get(name)

    def get_problem(self, flag: str) -> Optional[dict]:
        """Get posture problem definition by flag name (e.g., 'head_forward_posture')."""
        data = self._load("problems.json")
        return data.get(flag)

    def get_problems(self) -> dict:
        """Get all problem definitions."""
        return self._load("problems.json")

    def get_rom_norm(self, joint: str) -> Optional[dict]:
        """Get ROM norm for a joint (e.g., 'left_knee', 'right_hip')."""
        data = self._load("rom_norms.json")
        return data.get(joint)

    def get_threshold(self, name: str) -> Optional[dict]:
        """Get threshold definition by name."""
        data = self._load("thresholds.json")
        return data.get(name)

    def get_thresholds(self) -> dict:
        """Get all threshold definitions."""
        return self._load("thresholds.json")

    def reload(self):
        """Clear cache and re-read all files on next access."""
        self._cache.clear()


# Singleton instance
knowledge_base = KnowledgeBase()
