import threading

class Connection:
    """Simulated database connection."""
    
    def __init__(self, conn_id):
        self.conn_id = conn_id
        self.in_transaction = False
        self.query_count = 0
        self.is_open = True
    
    def begin(self):
        self.in_transaction = True
    
    def commit(self):
        self.in_transaction = False
    
    def rollback(self):
        self.in_transaction = False
    
    def execute(self, query):
        self.query_count += 1
        return f"result_{self.query_count}"
    
    def close(self):
        self.is_open = False


class ConnectionPool:
    """Simple connection pool."""
    
    def __init__(self, max_size=5):
        self.max_size = max_size
        self._available = []
        self._in_use = set()
        self._next_id = 0
        self._lock = threading.Lock()
    
    def acquire(self):
        """Get a connection from the pool."""
        with self._lock:
            if self._available:
                conn = self._available.pop()
                self._in_use.add(conn.conn_id)
                return conn
            
            if len(self._in_use) < self.max_size:
                conn = Connection(self._next_id)
                self._next_id += 1
                self._in_use.add(conn.conn_id)
                return conn
            
            raise RuntimeError("Pool exhausted")
    
    def release(self, conn):
        """Return a connection to the pool."""
        with self._lock:
            if conn.conn_id in self._in_use:
                self._in_use.discard(conn.conn_id)
                # BUG: doesn't reset connection state before returning to pool
                # Transaction state and query count carry over to next user
                self._available.append(conn)
