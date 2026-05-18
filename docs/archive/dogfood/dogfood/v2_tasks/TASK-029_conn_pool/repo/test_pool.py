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
