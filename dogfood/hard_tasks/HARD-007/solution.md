# Solution for HARD-007: Auth Chain Bug

## Bug 1: Middleware Checks Permissions Before Auth

In `src/middleware.py`, the `process_request` method checks permissions BEFORE authentication:

```python
def process_request(self, request):
    # BUG: Checking permissions first!
    if not self.permissions.check_permission(user_id, "read"):
        return {"error": "Permission denied"}

    # Then authenticating
    user = self.auth.authenticate(request.get("username"), request.get("password"))
```

This is wrong because you shouldn't check permissions for a user that hasn't been authenticated yet.

### Fix 1 (middleware.py):
Swap the order - authenticate first, then check permissions:

```python
def process_request(self, request):
    # Correct: authenticate first
    user = self.auth.authenticate(request.get("username"), request.get("password"))
    if user is None:
        return {"error": "Authentication failed"}

    # Then check permissions
    if not self.permissions.check_permission(user["id"], "read"):
        return {"error": "Permission denied"}
```

## Bug 2: Permissions Cache Returns Stale Results

In `src/permissions.py`, the `check_permission` method caches results incorrectly:

```python
def check_permission(self, user_id: str, permission: str) -> bool:
    cache_key = f"{user_id}:{permission}"
    if cache_key in self._cache:
        return self._cache[cache_key]  # BUG: Returns cached result even if user role changed!
```

The cache doesn't account for the user's role potentially changing. If a user's role is updated (e.g., from "user" to "admin"), the cached "denied" result would still be returned.

### Fix 2 (permissions.py):
Invalidate cache when user roles are updated:

```python
def update_user_role(self, user_id: str, new_role: str) -> None:
    self._user_roles[user_id] = new_role
    # Invalidate all cached permissions for this user
    keys_to_delete = [k for k in self._cache if k.startswith(f"{user_id}:")]
    for key in keys_to_delete:
        del self._cache[key]
```

Or alternatively, include the user's current role in the cache key:
```python
cache_key = f"{user_id}:{permission}:{self._user_roles.get(user_id)}"
```

## Why Both Bugs Together Are Dangerous

1. Bug 1 (wrong order) means permissions are checked on unauthenticated requests
2. Bug 2 (stale cache) means even after proper authentication, wrong cached results may be returned
3. Combined with the cache returning False for unknown users, an unauthenticated user might get cached "denied" results for one resource but then access another resource that wasn't cached yet
