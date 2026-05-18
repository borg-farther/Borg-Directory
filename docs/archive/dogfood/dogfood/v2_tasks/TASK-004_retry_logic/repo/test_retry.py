import sys
sys.path.insert(0, '.')
from retry import RetryHandler, PartialSuccess

def test_exponential_backoff():
    """Delays should be 1, 2, 4 for 3 retries."""
    calls = []
    def failing_func():
        calls.append(1)
        raise ValueError("fail")
    
    handler = RetryHandler(max_retries=3, base_delay=1.0)
    try:
        handler.execute(failing_func)
    except ValueError:
        pass
    
    assert len(calls) == 4, f"Expected 4 calls, got {len(calls)}"
    assert handler._delays == [1.0, 2.0, 4.0], f"Wrong delays: {handler._delays}"

def test_partial_success_continues_backoff():
    """After partial success, backoff should NOT reset to base."""
    call_count = [0]
    
    def partial_then_fail():
        call_count[0] += 1
        if call_count[0] == 1:
            raise ValueError("total fail")
        elif call_count[0] == 2:
            raise PartialSuccess("partial")
        elif call_count[0] == 3:
            raise ValueError("fail again")
        else:
            return "success"
    
    handler = RetryHandler(max_retries=5, base_delay=1.0)
    result = handler.execute(partial_then_fail)
    assert result == "success", f"Expected success, got {result}"
    
    # Delays should be increasing, NOT resetting after partial success
    # Expected: 1.0 (after fail), 2.0 (after partial), 4.0 (after fail again)
    assert len(handler._delays) >= 3, f"Expected >= 3 delays, got {handler._delays}"
    assert handler._delays[1] > handler._delays[0], \
        f"Backoff should increase after partial success: {handler._delays}"

if __name__ == "__main__":
    tests = [test_exponential_backoff, test_partial_success_continues_backoff]
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
