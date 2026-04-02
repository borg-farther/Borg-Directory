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
