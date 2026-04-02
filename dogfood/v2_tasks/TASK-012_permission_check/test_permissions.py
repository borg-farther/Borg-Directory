"""Test cases for permission checking."""
import sys
sys.path.insert(0, '/root/hermes-workspace/borg/dogfood/v2_tasks/TASK-012_permission_check')

from permissions import (
    check_permission, grant_permission, revoke_permission,
    has_permission, parse_permission_string,
    READ, WRITE, EXECUTE, PermissionError
)


def test_basic_permissions():
    """Test basic permission bit operations."""
    # User with all permissions
    user = READ | WRITE | EXECUTE
    
    assert has_permission(user, READ), "Should have read"
    assert has_permission(user, WRITE), "Should have write"
    assert has_permission(user, EXECUTE), "Should have execute"
    print("test_basic_permissions: PASS")


def test_grant_permission():
    """Test granting a permission."""
    user = READ
    user = grant_permission(user, WRITE)
    
    assert has_permission(user, READ), "Should still have read"
    assert has_permission(user, WRITE), "Should now have write"
    assert not has_permission(user, EXECUTE), "Should not have execute"
    print("test_grant_permission: PASS")


def test_revoke_permission():
    """Test revoking a permission."""
    user = READ | WRITE | EXECUTE
    user = revoke_permission(user, WRITE)
    
    assert has_permission(user, READ), "Should still have read"
    assert not has_permission(user, WRITE), "Should not have write"
    assert has_permission(user, EXECUTE), "Should still have execute"
    print("test_revoke_permission: PASS")


def test_check_single_permission():
    """Test checking a single permission."""
    user = READ | WRITE  # No execute
    
    # Should succeed for read
    check_permission(user, READ)
    
    # Should fail for execute
    try:
        check_permission(user, EXECUTE)
        assert False, "Should have raised PermissionError"
    except PermissionError:
        pass
    
    print("test_check_single_permission: PASS")


def test_check_multiple_permissions():
    """
    Test checking multiple permissions at once.
    
    User has READ and WRITE but not EXECUTE.
    Checking for READ|WRITE should succeed.
    Checking for READ|EXECUTE should FAIL because user lacks EXECUTE.
    """
    user = READ | WRITE  # No EXECUTE
    
    # Should succeed - user has both READ and WRITE
    check_permission(user, READ | WRITE)
    
    # Should fail - user doesn't have EXECUTE
    try:
        # This is the critical test: checking for READ|EXECUTE
        # Correct behavior: user has READ but not EXECUTE, so should FAIL
        # Buggy behavior with OR: READ|WRITE|EXECUTE = 7 (truthy), so passes!
        check_permission(user, READ | EXECUTE)
        assert False, "Should have raised PermissionError for missing EXECUTE"
    except PermissionError:
        pass
    
    print("test_check_multiple_permissions: PASS")


def test_parse_permission_string():
    """Test parsing permission strings."""
    assert parse_permission_string('r') == READ
    assert parse_permission_string('w') == WRITE
    assert parse_permission_string('x') == EXECUTE
    assert parse_permission_string('rw') == READ | WRITE
    assert parse_permission_string('rwx') == READ | WRITE | EXECUTE
    print("test_parse_permission_string: PASS")


def test_permission_denied_for_missing():
    """
    Critical test: permission check must fail if ANY required permission is missing.
    """
    user = READ | WRITE  # No EXECUTE
    
    # The bug causes this to incorrectly pass because:
    # user | EXECUTE = 6 | 1 = 7 (truthy)
    # But correct behavior is:
    # user & EXECUTE = 6 & 1 = 0 (falsy, should raise)
    
    try:
        check_permission(user, EXECUTE)
        raise AssertionError("Bug: Permission check passed for missing EXECUTE!")
    except PermissionError:
        pass  # This is correct behavior
    
    print("test_permission_denied_for_missing: PASS")


if __name__ == "__main__":
    test_basic_permissions()
    test_grant_permission()
    test_revoke_permission()
    test_check_single_permission()
    test_check_multiple_permissions()
    test_parse_permission_string()
    test_permission_denied_for_missing()
    print("\nAll tests passed!")
