"""State definitions for the state machine."""

from enum import Enum


class State(Enum):
    """Valid states for the state machine."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class StateInfo:
    """Additional metadata about a state."""
    
    def __init__(self, state: State, description: str = ""):
        self.state = state
        self.description = description
        self.enter_count = 0
        self.exit_count = 0
    
    def __repr__(self):
        return f"StateInfo({self.state.value}, enter={self.enter_count}, exit={self.exit_count})"


# State descriptions
STATE_DESCRIPTIONS = {
    State.IDLE: "Initial state, ready to start",
    State.RUNNING: "Currently executing",
    State.PAUSED: "Execution paused, can resume",
    State.STOPPED: "Execution stopped, cannot resume",
    State.ERROR: "Error state, needs recovery"
}
