"""Unit tests for DualModeScorer and FMSScoringEngine."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.scoring import DualModeScorer
from models.fms.scoring import FMSScoringEngine


class TestDualModeScorerBasic:
    def test_good_squat_passes(self):
        """A squat with good angles should pass basic mode."""
        angles = {
            'left_knee': 80, 'right_knee': 82,
            'trunk_tilt': 10,
        }
        result = DualModeScorer.score_basic(angles, 'squat')
        assert result['passed'] is True
        assert result['result'] == 'pass'

    def test_trunk_lean_detected(self):
        """Excessive trunk tilt should trigger warning."""
        angles = {
            'left_knee': 80, 'right_knee': 82,
            'trunk_tilt': 50,  # above the 45-degree threshold
        }
        result = DualModeScorer.score_basic(angles, 'squat')
        assert result['result'] == 'warning'
        assert any(w['joint'] == 'trunk' for w in result['warnings'])


class TestDualModeScorerAdvanced:
    def test_perfect_score(self):
        """Angles within optimal range should score near 100."""
        angles = {
            'left_knee': 85, 'right_knee': 85,
            'trunk_tilt': 5,
        }
        result = DualModeScorer.score_advanced(angles, 'squat')
        assert result['score'] >= 90
        assert result['quality'] == 'excellent'

    def test_rom_insufficient(self):
        """Shallow squat should be penalized."""
        angles = {
            'left_knee': 140, 'right_knee': 140,  # almost no knee bend
            'trunk_tilt': 5,
        }
        result = DualModeScorer.score_advanced(angles, 'squat')
        assert result['score'] < 75  # Should be penalized
        assert any('ROM insufficient' in p['message'] for p in result['penalties'])

    def test_asymmetry_penalized(self):
        """Left-right asymmetry should reduce score."""
        angles = {
            'left_knee': 80, 'right_knee': 110,  # 30-degree asymmetry
            'trunk_tilt': 5,
        }
        result = DualModeScorer.score_advanced(angles, 'squat')
        assert any('asymmetry' in p['message'] for p in result['penalties'])

    def test_score_never_negative(self):
        """Score should be clamped to >= 0."""
        angles = {
            'left_knee': 0, 'right_knee': 0,
            'trunk_tilt': 90,
        }
        result = DualModeScorer.score_advanced(angles, 'squat')
        assert result['score'] >= 0

    def test_hyperextension_penalized(self):
        """Exceeding max_angle should be penalized."""
        angles = {
            'left_knee': 175, 'right_knee': 175,  # past max_angle (160 for squat)
            'trunk_tilt': 10,
        }
        result = DualModeScorer.score_advanced(angles, 'squat')
        assert any('hyperextension' in p['message'] for p in result.get('penalties', []))


class TestFMSScoringEngine:
    def test_flexibility_score_capped(self):
        """Flexibility score should never exceed 100."""
        engine = FMSScoringEngine()
        # Perfect/beyond-perfect inputs
        score = engine.score_flexibility(depth_cm=50, trunk_angle=0, arm_ratio=1.0)
        assert score.score <= 100.0

    def test_upper_limb_perfect(self):
        """Zero distance should give 100."""
        engine = FMSScoringEngine()
        score = engine.score_upper_limb(distance_cm=0)
        assert pytest.approx(score.score, abs=1) == 100.0

    def test_upper_limb_large_distance(self):
        """Large distance should give low score."""
        engine = FMSScoringEngine()
        score = engine.score_upper_limb(distance_cm=20)
        assert score.score < 20

    def test_core_duration_perfect(self):
        """2+ minutes should be perfect."""
        engine = FMSScoringEngine()
        score = engine.score_core(duration_sec=130)
        assert pytest.approx(score.score, abs=1) == 100.0

    def test_symmetry_perfect(self):
        """Identical left/right should be 100."""
        engine = FMSScoringEngine()
        score = engine.score_symmetry(left=80, right=80)
        assert pytest.approx(score.score, abs=1) == 100.0

    def test_symmetry_large_diff(self):
        """Large left-right difference should reduce score."""
        engine = FMSScoringEngine()
        score = engine.score_symmetry(left=80, right=40)
        assert score.score < 60

    def test_balance_score_normal(self):
        engine = FMSScoringEngine()
        score = engine.score_balance(duration_sec=30)
        assert 0 <= score.score <= 100


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
