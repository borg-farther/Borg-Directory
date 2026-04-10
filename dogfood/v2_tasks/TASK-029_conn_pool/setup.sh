#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/pool.py << 'PYEOF'
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
PYEOF

cat > repo/test_pool.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from pool import ConnectionPool

def test_connection_reuse_clean():
    """Reused connections should be in clean state."""
    pool = ConnectionPool(max_size=1)
    
    # First user starts a transaction
    conn1 = pool.acquire()
    conn1.begin()
    conn1.execute("INSERT ...")
    assert conn1.in_transaction == True
    assert conn1.query_count == 1
    pool.release(conn1)
    
    # Second user gets same connection — should be clean
    conn2 = pool.acquire()
    assert conn2.conn_id == conn1.conn_id, "Should reuse same connection"
    assert conn2.in_transaction == False, f"Connection should not be in transaction, got {conn2.in_transaction}"
    assert conn2.query_count == 0, f"Query count should be reset, got {conn2.query_count}"

def test_rollback_on_release():
    """Active transaction should be rolled back on release."""
    pool = ConnectionPool(max_size=2)
    
    conn = pool.acquire()
    conn.begin()
    pool.release(conn)
    
    conn2 = pool.acquire()
    assert conn2.in_transaction == False, "Transaction should be rolled back"

def test_pool_size():
    pool = ConnectionPool(max_size=2)
    c1 = pool.acquire()
    c2 = pool.acquire()
    try:
        c3 = pool.acquire()
        assert False, "Should raise RuntimeError"
    except RuntimeError:
        pass
    
    pool.release(c1)
    c3 = pool.acquire()  # Should work now
    assert c3.conn_id == c1.conn_id

if __name__ == "__main__":
    tests = [test_connection_reuse_clean, test_rollback_on_release, test_pool_size]
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
