import sys
sys.path.insert(0, '.')
from graph import Graph

def test_bfs_no_duplicates():
    """BFS should visit each node exactly once."""
    g = Graph()
    # Diamond: A->B, A->C, B->D, C->D
    g.add_edge("A", "B")
    g.add_edge("A", "C")
    g.add_edge("B", "D")
    g.add_edge("C", "D")
    
    result = g.bfs("A")
    assert len(result) == len(set(result)), f"Duplicates in BFS: {result}"
    assert set(result) == {"A", "B", "C", "D"}, f"Missing nodes: {result}"

def test_bfs_cycle():
    """BFS should handle cycles without infinite loop."""
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")
    
    result = g.bfs("A")
    assert len(result) == 3, f"Expected 3 nodes, got {len(result)}: {result}"
    assert set(result) == {"A", "B", "C"}, f"Wrong nodes: {result}"

def test_shortest_path_cycle():
    """Shortest path should work with cycles in graph."""
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("B", "C")
    g.add_edge("C", "A")  # cycle
    g.add_edge("B", "D")
    
    dist = g.shortest_path("A", "D")
    assert dist == 2, f"Expected 2, got {dist}"

def test_shortest_path_unreachable():
    g = Graph()
    g.add_edge("A", "B")
    g.add_edge("C", "D")
    
    dist = g.shortest_path("A", "D")
    assert dist == -1, f"Expected -1, got {dist}"

if __name__ == "__main__":
    import signal
    signal.alarm(5)  # 5 second timeout to catch infinite loops
    
    tests = [test_bfs_no_duplicates, test_bfs_cycle, test_shortest_path_cycle, test_shortest_path_unreachable]
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
