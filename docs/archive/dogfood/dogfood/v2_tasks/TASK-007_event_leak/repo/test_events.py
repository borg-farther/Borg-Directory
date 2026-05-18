import sys
sys.path.insert(0, '.')
from events import EventBus, Widget

def test_unsubscribe_works():
    """After destroy(), widget should not receive events."""
    bus = EventBus()
    w = Widget("w1", bus)
    
    bus.publish("update", "msg1")
    assert w.received == ["msg1"], f"Should receive before destroy: {w.received}"
    
    w.destroy()
    bus.publish("update", "msg2")
    assert w.received == ["msg1"], f"Should NOT receive after destroy: {w.received}"

def test_handler_count_after_unsubscribe():
    """Handler count should decrease after unsubscribe."""
    bus = EventBus()
    w1 = Widget("w1", bus)
    w2 = Widget("w2", bus)
    
    assert bus.handler_count("update") == 2
    w1.destroy()
    assert bus.handler_count("update") == 1, f"Expected 1 handler, got {bus.handler_count('update')}"

def test_multiple_destroy_safe():
    """Calling destroy() twice should not crash."""
    bus = EventBus()
    w = Widget("w1", bus)
    w.destroy()
    try:
        w.destroy()  # Should not raise
    except ValueError:
        print("FAIL: second destroy() raised ValueError")
        sys.exit(1)

if __name__ == "__main__":
    tests = [test_unsubscribe_works, test_handler_count_after_unsubscribe, test_multiple_destroy_safe]
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
