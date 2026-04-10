#!/bin/bash
# TASK-012: Permission check with bitwise operator bug

mkdir -p /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-012_permission_check

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-012_permission_check/permissions.py << 'EOF'
"""Permission checking module with a subtle bitwise operator bug."""

import os


# Permission bits
READ = 4
WRITE = 2
EXECUTE = 1

# Permission strings for display
PERM_NAMES = {
    'r': READ,
    'w': WRITE,
    'x': EXECUTE
}


class PermissionError(Exception):
    """Raised when a permission check fails."""
    pass


def check_permission(user_perms, required_perms):
    """
    Check if user has all required permissions.
    
    Args:
        user_perms: Integer permission bits for the user
        required_perms: Integer permission bits required
        
    Returns:
        True if user has all required permissions
        
    Raises:
        PermissionError: If user lacks any required permission
    """
    # BUG: Using OR instead of AND!
    # This returns True if user has ANY of the required permissions,
    # not ALL of them.
    if user_perms | required_perms:
        return True
    else:
        raise PermissionError(
            f"User has {user_perms}, needs {required_perms}"
        )


def grant_permission(user_perms, perm_to_grant):
    """Grant a permission to user."""
    return user_perms | perm_to_grant


def revoke_permission(user_perms, perm_to_revoke):
    """Revoke a permission from user."""
    return user_perms & ~perm_to_revoke


def has_permission(user_perms, perm):
    """Check if user has a specific permission bit."""
    return bool(user_perms & perm)


def parse_permission_string(perm_str):
    """Parse permission string like 'rw' into permission bits."""
    perms = 0
    for char in perm_str:
        if char in PERM_NAMES:
            perms |= PERM_NAMES[char]
    return perms


def main():
    """Demonstrate the permission checking bug."""
    
    # User has read and write permissions
    user = READ | WRITE  # = 6
    
    print(f"User permissions: {user} (binary: {bin(user)})")
    print(f"READ={READ}, WRITE={WRITE}, EXECUTE={EXECUTE}")
    
    # Check if user can read (should succeed)
    try:
        check_permission(user, READ)
        print("✓ User can READ")
    except PermissionError as e:
        print(f"✗ User cannot READ: {e}")
    
    # Check if user can execute (should fail)
    try:
        check_permission(user, EXECUTE)
        print("✓ User can EXECUTE")
    except PermissionError as e:
        print(f"✗ User cannot EXECUTE: {e}")
    
    # Check if user can read AND write (should succeed)
    try:
        check_permission(user, READ | WRITE)
        print("✓ User can READ and WRITE")
    except PermissionError as e:
        print(f"✗ User cannot READ and WRITE: {e}")
    
    # BUG: With the OR bug, check_permission(user, EXECUTE) returns True
    # because user(6) | EXECUTE(1) = 7, and 7 is truthy!
    # But the correct behavior is that 7 & 1 = 1 (has execute), so it should
    # return True if using & (bitwise AND).
    # 
    # With the buggy OR: 6 | 1 = 7 (truthy), so permission is "granted"
    # even though user doesn't have execute permission!
    
    print("\n--- Demonstrating the bug ---")
    result = user | EXECUTE  # This is what the buggy code does
    print(f"user({user}) | EXECUTE({EXECUTE}) = {result} (truthy={bool(result)})")
    print("This incorrectly grants execute permission!")
    
    correct_result = user & EXECUTE
    print(f"Correct: user({user}) & EXECUTE({EXECUTE}) = {correct_result} (truthy={bool(correct_result)})")


if __name__ == "__main__":
    main()
EOF

cat > /root/hermes-workspace/borg/dogfood/v2_tasks/TASK-012_permission_check/test_permissions.py << 'EOF'
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
EOF
