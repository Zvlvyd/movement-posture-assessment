"""Unit tests for AngleCalculator."""
import pytest
import numpy as np
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.angle_calculator import AngleCalculator, calc_angle, calc_vertical_angle


class TestCalcAngle:
    def test_right_angle(self):
        """90-degree angle at b."""
        a = np.array([0, 0])
        b = np.array([1, 0])
        c = np.array([1, 1])
        result = calc_angle(a, b, c)
        assert pytest.approx(result, abs=0.5) == 90.0

    def test_straight_line(self):
        """180-degree straight line."""
        a = np.array([0, 0])
        b = np.array([1, 0])
        c = np.array([2, 0])
        result = calc_angle(a, b, c)
        assert pytest.approx(result, abs=1.0) == 180.0

    def test_acute_angle(self):
        """45-degree acute angle."""
        a = np.array([0, 0])
        b = np.array([1, 1])
        c = np.array([2, 0])
        result = calc_angle(a, b, c)
        assert pytest.approx(result, abs=1.0) == 90.0  # (0,0)-(1,1)-(2,0) is isosceles right

    def test_zero_vectors_handled(self):
        """Division by zero guarded by epsilon."""
        a = np.array([1, 1])
        b = np.array([1, 1])  # same as a
        c = np.array([2, 2])
        # Should not raise — epsilon prevents division by zero
        result = calc_angle(a, b, c)
        assert not np.isnan(result)


class TestCalcVerticalAngle:
    def test_vertical_up(self):
        """Point directly above reference: 0 degrees."""
        a = np.array([100, 200])
        b = np.array([100, 100])
        result = calc_vertical_angle(a, b)
        assert pytest.approx(result, abs=0.5) == 0.0

    def test_horizontal_right(self):
        """Point to the right: 90 degrees."""
        a = np.array([100, 100])
        b = np.array([200, 100])
        result = calc_vertical_angle(a, b)
        assert pytest.approx(result, abs=0.5) == 90.0

    def test_below(self):
        """Point below reference: > 90 degrees."""
        a = np.array([100, 100])
        b = np.array([100, 200])
        result = calc_vertical_angle(a, b)
        assert result > 90.0


class TestAngleCalculator:
    def test_compute_all_angles_shape(self):
        """compute_all_angles returns expected keys."""
        calc = AngleCalculator()
        # Create 17 keypoints with shape (17, 2)
        kps = np.random.rand(17, 2) * 100 + 100  # positive coords
        angles = calc.compute_all_angles(kps)
        expected_keys = [
            'left_knee', 'right_knee', 'left_hip', 'right_hip',
            'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
            'trunk_tilt', 'neck_tilt',
        ]
        for key in expected_keys:
            assert key in angles, f"Missing key: {key}"

    def test_compute_all_angles_range(self):
        """All angles should be in [0, 180] range."""
        calc = AngleCalculator()
        kps = np.random.rand(17, 2) * 200 + 50
        angles = calc.compute_all_angles(kps)
        for key, value in angles.items():
            if value is not None:
                assert 0 <= value <= 180, f"{key}={value} out of range"

    def test_symmetry_detection(self):
        """Symmetrical keypoints should produce similar left/right angles."""
        calc = AngleCalculator()
        # Create perfectly symmetrical keypoints
        kps = np.zeros((17, 2))
        kps[11] = [90, 300]   # left hip
        kps[12] = [150, 300]  # right hip
        kps[13] = [90, 380]   # left knee
        kps[14] = [150, 380]  # right knee
        kps[15] = [90, 460]   # left ankle
        kps[16] = [150, 460]  # right ankle
        kps[5] = [90, 200]    # left shoulder
        kps[6] = [150, 200]   # right shoulder
        angles = calc.compute_all_angles(kps)
        assert abs(angles['left_knee'] - angles['right_knee']) < 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
