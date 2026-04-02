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
