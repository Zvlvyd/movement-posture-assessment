# -*- coding: utf-8 -*-
"""
Multi-View Assessment Session State Management
In-memory session store with TTL-based expiry for the three-photo → verification flow.
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .multi_view_analyzer import MergedPostureFindings, ViewKeypoints
from .verification_mapper import VerificationMovement
from .velocity_analyzer import VelocityAsymmetryFinding
from .fusion_engine import FusionResult
from .rom_tracker import MovementROMResult


@dataclass
class MultiViewSession:
    """State for one multi-view assessment session."""
    session_id: str
    user_id: int
    created_at: float = field(default_factory=time.time)

    # Photo upload → keypoints
    front_keypoints: Optional[List[List[float]]] = None
    back_keypoints: Optional[List[List[float]]] = None
    side_keypoints: Optional[List[List[float]]] = None

    # Static analysis results
    merged_findings: Optional[MergedPostureFindings] = None

    # Generated verification plan
    verification_plan: List[VerificationMovement] = field(default_factory=list)

    # ROM verification results per movement index
    verification_results: Dict[int, List[MovementROMResult]] = field(default_factory=dict)

    # Velocity asymmetry findings across all verified movements
    velocity_findings: List[VelocityAsymmetryFinding] = field(default_factory=list)

    # ROM ratios for fusion (angle_key → ratio)
    rom_ratios: Dict[str, float] = field(default_factory=dict)

    # Final fusion result
    fusion_result: Optional[FusionResult] = None

    # Status tracking
    status: str = "created"  # created | photos_uploaded | analyzed | verification_ready | verified | fused
    record_id: Optional[int] = None  # DB record ID after persistence


class MultiViewSessionStore:
    """In-memory session store with TTL-based expiry and capacity limit."""

    DEFAULT_TTL = 1800  # 30 minutes
    MAX_SESSIONS = 100  # Prevent unbounded memory growth

    def __init__(self):
        self._sessions: Dict[str, MultiViewSession] = {}

    def create(self, user_id: int) -> MultiViewSession:
        """Create a new session. Evicts oldest expired sessions if at capacity."""
        # Evict oldest sessions if at capacity
        if len(self._sessions) >= self.MAX_SESSIONS:
            self.cleanup_expired()
        if len(self._sessions) >= self.MAX_SESSIONS:
            # Evict the oldest session as a last resort
            oldest_id = min(
                self._sessions.keys(),
                key=lambda sid: self._sessions[sid].created_at,
            )
            del self._sessions[oldest_id]

        session_id = str(uuid.uuid4())[:12]
        session = MultiViewSession(session_id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Optional[MultiViewSession]:
        """Get session by ID, returns None if expired or not found."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        # Check TTL expiry
        if time.time() - session.created_at > self.DEFAULT_TTL:
            del self._sessions[session_id]
            return None

        return session

    def update(self, session_id: str, **kwargs) -> Optional[MultiViewSession]:
        """Update session fields."""
        session = self.get(session_id)
        if session is None:
            return None
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)
        return session

    def delete(self, session_id: str):
        """Remove a session."""
        self._sessions.pop(session_id, None)

    def cleanup_expired(self):
        """Remove all expired sessions."""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.created_at > self.DEFAULT_TTL
        ]
        for sid in expired:
            del self._sessions[sid]

    def __len__(self):
        return len(self._sessions)


# Global store instance
multi_view_session_store = MultiViewSessionStore()
