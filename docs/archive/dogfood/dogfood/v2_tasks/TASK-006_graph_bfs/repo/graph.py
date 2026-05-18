from collections import deque

class Graph:
    """Directed graph with BFS traversal."""
    
    def __init__(self):
        self.adj = {}  # node -> [neighbors]
    
    def add_edge(self, src, dst):
        if src not in self.adj:
            self.adj[src] = []
        if dst not in self.adj:
            self.adj[dst] = []
        self.adj[src].append(dst)
    
    def bfs(self, start):
        """Return nodes in BFS order from start."""
        if start not in self.adj:
            return []
        
        result = []
        queue = deque([start])
        
        while queue:
            node = queue.popleft()
            result.append(node)
            # BUG: no visited set — revisits nodes in cyclic or diamond graphs
            for neighbor in self.adj[node]:
                queue.append(neighbor)
        
        return result
    
    def shortest_path(self, start, end):
        """Return shortest path length from start to end, or -1 if unreachable."""
        if start not in self.adj or end not in self.adj:
            return -1
        if start == end:
            return 0
        
        queue = deque([(start, 0)])
        
        while queue:
            node, dist = queue.popleft()
            for neighbor in self.adj[node]:
                if neighbor == end:
                    return dist + 1
                # BUG: no visited tracking — infinite loop on cycles
                queue.append((neighbor, dist + 1))
        
        return -1
