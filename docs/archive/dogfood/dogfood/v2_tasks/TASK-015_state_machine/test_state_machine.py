"""Test cases for state machine."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-015_state_machine')

from state_machine import StateMachine, StateMachineError


def test_initial_state():
    """Test initial state is IDLE."""
    sm = StateMachine()
    assert sm.get_state() == "IDLE"
    print("test_initial_state: PASS")


def test_transition_from_idle():
    """Test transition from IDLE to PROCESSING."""
    sm = StateMachine()
    sm.trigger("start", {"success": True})
    assert sm.get_state() == "PROCESSING"
    print("test_transition_from_idle: PASS")


def test_processing_to_completed():
    """
    Test that PROCESSING -> COMPLETED when success=True.
    
    BUG: Due to swapped guards, this goes to FAILED instead!
    """
    sm = StateMachine()
    
    # Go to PROCESSING
    sm.trigger("start", {"success": True})
    assert sm.get_state() == "PROCESSING"
    
    # Complete with success - should go to COMPLETED
    sm.trigger("finish", {"success": True})
    assert sm.get_state() == "COMPLETED", \
        f"Expected COMPLETED, got {sm.get_state()}"
    
    print("test_processing_to_completed: PASS")


def test_processing_to_failed():
    """
    Test that PROCESSING -> FAILED when success=False.
    
    BUG: Due to swapped guards, this goes to COMPLETED instead!
    """
    sm = StateMachine()
    
    # Go to PROCESSING
    sm.trigger("start", {"success": True})
    assert sm.get_state() == "PROCESSING"
    
    # Complete with failure - should go to FAILED
    sm.trigger("finish", {"success": False})
    assert sm.get_state() == "FAILED", \
        f"Expected FAILED, got {sm.get_state()}"
    
    print("test_processing_to_failed: PASS")


def test_full_success_path():
    """Test the full success path: IDLE -> PROCESSING -> COMPLETED."""
    sm = StateMachine()
    
    # Start
    sm.trigger("start", {"success": True})
    assert sm.get_state() == "PROCESSING"
    
    # Finish with success
    sm.trigger("finish", {"success": True})
    assert sm.get_state() == "COMPLETED"
    
    print("test_full_success_path: PASS")


def test_full_failure_path():
    """Test the full failure path: IDLE -> PROCESSING -> FAILED."""
    sm = StateMachine()
    
    # Start
    sm.trigger("start", {"success": True})
    assert sm.get_state() == "PROCESSING"
    
    # Finish with failure
    sm.trigger("finish", {"success": False})
    assert sm.get_state() == "FAILED"
    
    print("test_full_failure_path: PASS")


def test_cannot_transition_from_completed():
    """Test that no transitions are allowed from COMPLETED."""
    sm = StateMachine()
    sm.trigger("start", {"success": True})
    sm.trigger("finish", {"success": True})
    
    try:
        sm.trigger("start", {"success": True})
        assert False, "Should not allow transition from COMPLETED"
    except StateMachineError:
        pass
    
    print("test_cannot_transition_from_completed: PASS")


def test_cannot_transition_from_failed():
    """Test that no transitions are allowed from FAILED."""
    sm = StateMachine()
    sm.trigger("start", {"success": True})
    sm.trigger("finish", {"success": False})
    
    try:
        sm.trigger("start", {"success": True})
        assert False, "Should not allow transition from FAILED"
    except StateMachineError:
        pass
    
    print("test_cannot_transition_from_failed: PASS")


if __name__ == "__main__":
    test_initial_state()
    test_transition_from_idle()
    test_processing_to_completed()
    test_processing_to_failed()
    test_full_success_path()
    test_full_failure_path()
    test_cannot_transition_from_completed()
    test_cannot_transition_from_failed()
    print("\nAll tests passed!")
