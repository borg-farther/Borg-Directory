# DEBUG-006: SQLAlchemy N+1 Query Problem

## Problem
The `get_users_with_posts_n_plus_1` function in `src/queries.py` executes N+1 queries:
- 1 query to fetch all users
- N additional queries (one per user) to fetch their posts

## Task
Fix the N+1 query problem by using `joinedload` or `subqueryload` to eager-load posts.

## Verification
```bash
./check.sh
```

## Expected Fix
Use SQLAlchemy's `joinedload` or `subqueryload` to fetch users and posts in a single query or just 2 queries total.
