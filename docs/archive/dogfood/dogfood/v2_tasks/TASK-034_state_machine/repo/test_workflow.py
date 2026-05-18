import sys
sys.path.insert(0, '.')
from workflow import StateMachine

def test_valid_transition():
    sm = StateMachine()
    assert sm.transition("submitted") == True
    assert sm.state == "submitted"

def test_invalid_transition():
    """Cannot go from created directly to shipped."""
    sm = StateMachine()
    result = sm.transition("shipped")
    assert result == False, f"Should not allow created->shipped"
    assert sm.state == "created", f"State should not change on invalid transition"

def test_full_workflow():
    sm = StateMachine()
    assert sm.transition("submitted")
    assert sm.transition("approved")
    assert sm.transition("shipped")
    assert sm.transition("delivered")
    assert sm.state == "delivered"

def test_cannot_skip_states():
    sm = StateMachine()
    # Cannot go from created to approved (must submit first)
    assert sm.transition("approved") == False
    assert sm.state == "created"

def test_reject_resubmit():
    sm = StateMachine()
    sm.transition("submitted")
    sm.transition("rejected")
    assert sm.transition("submitted") == True  # Can resubmit
    assert sm.state == "submitted"

if __name__ == "__main__":
    tests = [test_valid_transition, test_invalid_transition, test_full_workflow, 
             test_cannot_skip_states, test_reject_resubmit]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
