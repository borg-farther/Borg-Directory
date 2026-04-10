import sys
sys.path.insert(0, '.')
from topo import topological_sort

def test_linear():
    graph = {"c": ["b"], "b": ["a"], "a": []}
    result = topological_sort(graph)
    assert result.index("a") < result.index("b") < result.index("c"), f"Wrong order: {result}"

def test_diamond():
    graph = {"d": ["b", "c"], "b": ["a"], "c": ["a"], "a": []}
    result = topological_sort(graph)
    assert result.index("a") < result.index("b"), f"a should come before b: {result}"
    assert result.index("a") < result.index("c"), f"a should come before c: {result}"
    assert result.index("b") < result.index("d"), f"b should come before d: {result}"

def test_cycle_detection():
    graph = {"a": ["b"], "b": ["c"], "c": ["a"]}
    try:
        result = topological_sort(graph)
        # If no exception, result should not contain all nodes
        # (cycle means not all nodes can be sorted)
        assert False, f"Should have raised ValueError for cycle, got: {result}"
    except ValueError:
        pass  # Expected

def test_self_loop():
    graph = {"a": ["a"]}
    try:
        topological_sort(graph)
        assert False, "Should detect self-loop"
    except ValueError:
        pass

if __name__ == "__main__":
    tests = [test_linear, test_diamond, test_cycle_detection, test_self_loop]
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
