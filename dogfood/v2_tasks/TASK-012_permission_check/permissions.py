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
    # Check if user has ALL required permissions using AND
    if user_perms & required_perms == required_perms:
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
