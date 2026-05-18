class StateMachine:
    """Simple state machine for order workflow."""
    
    TRANSITIONS = {
        "created": ["submitted", "cancelled"],
        "submitted": ["approved", "rejected"],
        "approved": ["shipped", "cancelled"],
        "rejected": ["submitted"],  # Can resubmit
        "shipped": ["delivered"],
        "delivered": [],
        "cancelled": [],
    }
    
    def __init__(self, initial="created"):
        self.state = initial
        self.history = [initial]
    
    def transition(self, new_state):
        """Transition to new state. Returns True if valid transition."""
        allowed = self.TRANSITIONS.get(self.state, [])
        
        # BUG: checks if new_state is in the KEYS of TRANSITIONS, 
        # not in the allowed transitions for current state
        if new_state in self.TRANSITIONS:
            self.state = new_state
            self.history.append(new_state)
            return True
        return False
    
    def can_transition(self, new_state):
        """Check if transition is valid without executing it."""
        allowed = self.TRANSITIONS.get(self.state, [])
        # This method is correct
        return new_state in allowed
    
    def reset(self):
        """Reset to initial state."""
        self.state = "created"
        self.history = ["created"]
