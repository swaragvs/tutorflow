"""Session state machine logic."""

from enum import Enum

from app.models import Session, SessionStatusEnum


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    
    def __init__(self, current_status: str, action: str):
        self.current_status = current_status
        self.action = action
        super().__init__(
            f"Invalid transition: {current_status} via {action}"
        )


class SessionLockedError(Exception):
    """Raised when attempting to modify a locked session."""
    
    def __init__(self, current_status: str):
        self.current_status = current_status
        super().__init__(
            f"Session is locked in {current_status} state"
        )


def transition_session(session: Session, action: str) -> None:
    """
    Transition a session to a new state based on the action.
    
    Legal transitions:
    - SCHEDULED → IN_PROGRESS (action="start")
    - IN_PROGRESS → COMPLETED (action="complete")
    - COMPLETED → AI_REVIEWED (action="trigger_ai_review")
    
    Any other transition raises InvalidTransitionError.
    
    Args:
        session: Session model instance
        action: Action being performed ("start", "complete", "trigger_ai_review")
        
    Raises:
        InvalidTransitionError: If transition is not allowed
    """
    current = session.status
    
    # Define allowed transitions
    allowed_transitions = {
        SessionStatusEnum.SCHEDULED: {
            "start": SessionStatusEnum.IN_PROGRESS,
        },
        SessionStatusEnum.IN_PROGRESS: {
            "complete": SessionStatusEnum.COMPLETED,
        },
        SessionStatusEnum.COMPLETED: {
            "trigger_ai_review": SessionStatusEnum.AI_REVIEWED,
        },
    }
    
    # Check if current state has any allowed transitions
    if current not in allowed_transitions:
        raise InvalidTransitionError(current.value, action)
    
    # Check if this action is allowed from current state
    if action not in allowed_transitions[current]:
        raise InvalidTransitionError(current.value, action)
    
    # Perform the transition
    new_status = allowed_transitions[current][action]
    session.status = new_status


def assert_session_not_locked(session: Session) -> None:
    """
    Check if a session is locked (COMPLETED or AI_REVIEWED).
    
    Raises:
        SessionLockedError: If session is locked
    """
    if session.status in (SessionStatusEnum.COMPLETED, SessionStatusEnum.AI_REVIEWED):
        raise SessionLockedError(session.status.value)
