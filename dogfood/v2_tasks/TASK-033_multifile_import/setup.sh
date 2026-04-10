#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo/myapp
cat > repo/myapp/__init__.py << 'PYEOF'
PYEOF

cat > repo/myapp/models.py << 'PYEOF'
class User:
    def __init__(self, name, email, role="user"):
        self.name = name
        self.email = email
        self.role = role
    
    def is_admin(self):
        return self.role == "admin"
    
    def display_name(self):
        return f"{self.name} <{self.email}>"
PYEOF

cat > repo/myapp/permissions.py << 'PYEOF'
from myapp.models import User

def can_edit(user, resource):
    """Check if user can edit a resource."""
    if user.is_admin():
        return True
    # BUG: checks resource.owner == user instead of resource.owner == user.name
    return resource.owner == user
    
def can_delete(user, resource):
    """Only admins and owners can delete."""
    if user.is_admin():
        return True
    # Same bug
    return resource.owner == user

def can_view(user, resource):
    """Anyone can view public resources, only owner/admin for private."""
    if resource.public:
        return True
    if user.is_admin():
        return True
    return resource.owner == user  # Same bug
PYEOF

cat > repo/myapp/resources.py << 'PYEOF'
class Resource:
    def __init__(self, name, owner, public=False):
        self.name = name
        self.owner = owner  # This is a string (user name)
        self.public = public
PYEOF

cat > repo/test_permissions.py << 'PYEOF'
import sys
sys.path.insert(0, 'repo')
from myapp.models import User
from myapp.permissions import can_edit, can_delete, can_view
from myapp.resources import Resource

def test_owner_can_edit():
    user = User("alice", "alice@test.com")
    res = Resource("doc1", "alice")
    assert can_edit(user, res), "Owner should be able to edit"

def test_non_owner_cannot_edit():
    user = User("bob", "bob@test.com")
    res = Resource("doc1", "alice")
    assert not can_edit(user, res), "Non-owner should not edit"

def test_admin_can_edit():
    admin = User("admin", "admin@test.com", role="admin")
    res = Resource("doc1", "alice")
    assert can_edit(admin, res), "Admin should be able to edit"

def test_owner_can_delete():
    user = User("alice", "alice@test.com")
    res = Resource("doc1", "alice")
    assert can_delete(user, res), "Owner should be able to delete"

def test_private_owner_view():
    user = User("alice", "alice@test.com")
    res = Resource("doc1", "alice", public=False)
    assert can_view(user, res), "Owner should view private resource"

def test_public_anyone_view():
    user = User("bob", "bob@test.com")
    res = Resource("doc1", "alice", public=True)
    assert can_view(user, res), "Anyone should view public resource"

if __name__ == "__main__":
    tests = [test_owner_can_edit, test_non_owner_cannot_edit, test_admin_can_edit,
             test_owner_can_delete, test_private_owner_view, test_public_anyone_view]
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
