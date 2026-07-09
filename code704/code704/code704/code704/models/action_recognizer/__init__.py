# -*- coding: utf-8 -*-
"""Action recognizer — FSM-based exercise action phase detection."""
from .state_machine import StateMachine, State, Transition
from .action_definitions import ActionDefinition, ACTION_DEFINITIONS, get_action_definition
from .squat_fsm import (
    create_squat_fsm, create_lunge_fsm, create_pushup_fsm,
    create_plank_fsm, create_shoulder_press_fsm,
    get_fsm_for_action, get_initial_state, get_fsm_context,
)
__all__ = [
    "StateMachine", "State", "Transition", "ActionDefinition",
    "ACTION_DEFINITIONS", "get_action_definition",
    "create_squat_fsm", "create_lunge_fsm", "create_pushup_fsm",
    "create_plank_fsm", "create_shoulder_press_fsm",
    "get_fsm_for_action", "get_initial_state", "get_fsm_context",
]
