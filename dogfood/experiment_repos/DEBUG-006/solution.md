# Solution: SQLAlchemy N+1 Query Fix

## The Problem
The original code fetches users first, then for each user, queries for their posts separately:

```python
users = session.query(User).all()
for user in users:
    posts = session.query(Post).filter(Post.user_id == user.id).all()
```

This results in 1 + N queries.

## The Fix
Use `joinedload` to eager-load the posts relationship in a single JOIN query:

```python
from sqlalchemy.orm import joinedload

def get_users_with_posts_fixed():
    engine = get_engine()
    Base.metadata.create_all(engine)
    session = get_session(engine)

    # Single query with JOIN - no N+1 problem
    users = session.query(User).options(joinedload(User.posts)).all()

    result = []
    for user in users:
        result.append({'name': user.name, 'posts': [p.title for p in user.posts]})

    return result
```

Or use `subqueryload` for a separate but pre-loaded query:

```python
from sqlalchemy.orm import subqueryload

users = session.query(User).options(subqueryload(User.posts)).all()
```

## Verification
The test checks that `counter.count <= 2`, ensuring the fix works.
