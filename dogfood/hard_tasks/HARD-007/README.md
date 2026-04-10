# HARD-007: Auth Chain Bug

## Task Description
You are debugging an authentication and authorization system where unauthorized users sometimes gain access they shouldn't have. The bug is subtle and involves the order of checks and caching issues.

## Problem
The auth system has three components:
1. `auth.py` - Authentication (verifies user credentials)
2. `permissions.py` - Authorization (checks user roles and permissions)
3. `middleware.py` - Combines auth and permissions in the request pipeline

The middleware is supposed to:
1. First authenticate the user (verify credentials)
2. Then authorize the user (check permissions based on roles)

However, there are two bugs:
1. The middleware checks permissions BEFORE authentication
2. The permissions module caches results incorrectly, returning stale data

## Your Goal
Find and fix both bugs so that all tests pass.

## Files
- `src/auth.py` - Authentication implementation
- `src/permissions.py` - Permission checking with caching
- `src/middleware.py` - Request pipeline combining auth and permissions
- `tests/test_auth.py` - Test suite

## Expected Behavior
- Authentication must always happen before authorization
- Permission cache must be invalidated when user roles change
- Users should only access resources they have permission for
