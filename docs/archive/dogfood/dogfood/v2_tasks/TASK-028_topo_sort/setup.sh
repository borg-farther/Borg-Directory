#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/topo.py << 'PYEOF'
def topological_sort(graph):
    """
    Topological sort of a directed acyclic graph.
    graph: dict mapping node -> list of dependencies (nodes this node depends on)
    Returns: list of nodes in dependency order (dependencies first)
    Raises ValueError if cycle detected.
    """
    # Build in-degree count and adjacency
    in_degree = {}
    adj = {}  # node -> nodes that depend on it
    
    for node in graph:
        if node not in in_degree:
            in_degree[node] = 0
        if node not in adj:
            adj[node] = []
        for dep in graph[node]:
            if dep not in in_degree:
                in_degree[dep] = 0
            if dep not in adj:
                adj[dep] = []
            adj[dep].append(node)
            in_degree[node] += 1
    
    # Start with nodes that have no dependencies
    queue = [n for n in in_degree if in_degree[n] == 0]
    result = []
    
    while queue:
        node = queue.pop(0)
        result.append(node)
        for dependent in adj[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    
    # BUG: doesn't check if all nodes were processed (cycle detection)
    return result
PYEOF

cat > repo/test_topo.py << 'PYEOF'
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
PYEOF
