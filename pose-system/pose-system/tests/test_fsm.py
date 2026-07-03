"""Unit tests for FSM action recognition state machines."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from models.action_recognizer.squat_fsm import (
    create_squat_fsm, create_lunge_fsm, create_pushup_fsm,
    create_plank_fsm, create_shoulder_press_fsm,
    create_jumping_jack_fsm, create_deadlift_fsm,
    get_fsm_context, get_initial_state, get_fsm_for_action,
)


def _run_fsm_sequence(fsm, angle_sequence, ctx_key='knee_angle'):
    """Helper: feed a sequence of angles into an FSM and count completions."""
    completions = 0
    for angle in angle_sequence:
        ctx = {ctx_key: angle}
        fsm.update(ctx)
        if fsm.current_state == 'complete':
            completions += 1
    return completions


class TestSquatFSM:
    def test_complete_squat_cycle(self):
        """A full squat cycle: standing -> descending -> bottom -> ascending -> complete."""
        fsm = create_squat_fsm()
        fsm.start()
        # standing (180) -> descending (< 150)
        fsm.update({'knee_angle': 180.0})
        assert fsm.current_state == 'standing'
        fsm.update({'knee_angle': 130.0})
        assert fsm.current_state == 'descending'
        # descending -> bottom (< 90)
        fsm.update({'knee_angle': 80.0})
        assert fsm.current_state == 'bottom'
        # bottom -> ascending (> 100)
        fsm.update({'knee_angle': 120.0})
        assert fsm.current_state == 'ascending'
        # ascending -> complete (> 155)
        fsm.update({'knee_angle': 165.0})
        assert fsm.current_state == 'complete'

    def test_incomplete_squat_no_count(self):
        """Shallow squat should not complete."""
        fsm = create_squat_fsm()
        fsm.start()
        fsm.update({'knee_angle': 180.0})
        fsm.update({'knee_angle': 140.0})  # descending
        fsm.update({'knee_angle': 100.0})  # not deep enough for bottom
        fsm.update({'knee_angle': 160.0})  # ascending but never hit bottom
        # Should not reach complete
        assert fsm.current_state != 'complete'

    def test_missing_angle_defaults_to_standing(self):
        """When knee_angle is missing, defaults should prevent false positives."""
        fsm = create_squat_fsm()
        fsm.start()
        fsm.update({})  # missing knee_angle → default 180
        assert fsm.current_state == 'standing'

    def test_loop_back_prevents_double_count(self):
        """After completing, staying upright should not count again."""
        fsm = create_squat_fsm()
        fsm.start()
        # Complete one rep
        for angle in [180, 130, 80, 120, 165]:
            fsm.update({'knee_angle': angle})
        assert fsm.current_state == 'complete'
        # Stay upright — should go back to standing, not count again
        fsm.update({'knee_angle': 170})
        assert fsm.current_state == 'standing'


class TestLungeFSM:
    def test_lunge_cycle(self):
        fsm = create_lunge_fsm()
        fsm.start()
        fsm.update({'front_knee_angle': 180})
        assert fsm.current_state == 'standing'
        fsm.update({'front_knee_angle': 130})
        assert fsm.current_state == 'lunging'
        fsm.update({'front_knee_angle': 80})
        assert fsm.current_state == 'bottom'
        fsm.update({'front_knee_angle': 120})
        assert fsm.current_state == 'recovering'
        fsm.update({'front_knee_angle': 165})
        assert fsm.current_state == 'complete'


class TestPushupFSM:
    def test_pushup_cycle(self):
        fsm = create_pushup_fsm()
        fsm.start()
        fsm.update({'elbow_angle': 180})  # top
        assert fsm.current_state == 'top'
        fsm.update({'elbow_angle': 130})  # descending
        assert fsm.current_state == 'descending'
        fsm.update({'elbow_angle': 70})   # bottom
        assert fsm.current_state == 'bottom'
        fsm.update({'elbow_angle': 120})  # ascending
        assert fsm.current_state == 'ascending'
        fsm.update({'elbow_angle': 170})  # complete
        assert fsm.current_state == 'complete'


class TestPlankFSM:
    def test_plank_ready_to_holding(self):
        fsm = create_plank_fsm()
        fsm.start()
        fsm.update({'hip_angle': 170})  # valid holding angle
        assert fsm.current_state == 'holding'

    def test_plank_droop_detected(self):
        fsm = create_plank_fsm()
        fsm.start()
        fsm.update({'hip_angle': 170})  # ready -> holding
        fsm.update({'hip_angle': 150})  # holding -> drooping
        assert fsm.current_state == 'drooping'


class TestFSMContext:
    def test_or_fallback_on_none(self):
        """When left angle is None, should fall back to right angle."""
        ctx = get_fsm_context('squat', {'left_knee': None, 'right_knee': 120.0})
        assert ctx['knee_angle'] == 120.0

    def test_or_fallback_on_zero(self):
        """When left angle is 0.0, should NOT fall through (fixed)."""
        ctx = get_fsm_context('squat', {'left_knee': 0.0, 'right_knee': 120.0})
        assert ctx['knee_angle'] == 0.0

    def test_both_missing_defaults_to_180(self):
        ctx = get_fsm_context('squat', {})
        assert ctx['knee_angle'] == 180.0


class TestGetInitialState:
    def test_squat_start(self):
        assert get_initial_state('squat') == 'standing'

    def test_pushup_start(self):
        assert get_initial_state('pushup') == 'top'

    def test_plank_start(self):
        assert get_initial_state('plank') == 'ready'

    def test_unknown_action(self):
        assert get_initial_state('unknown') == 'standing'


class TestGetFSMForAction:
    def test_returns_fsm_for_valid_actions(self):
        for action in ['squat', 'lunge', 'pushup', 'plank',
                       'shoulder_press', 'jumping_jack', 'deadlift']:
            fsm = get_fsm_for_action(action)
            assert fsm is not None
            assert fsm.name == action.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
