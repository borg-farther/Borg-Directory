# HARD-005: Database Layer Corruption

## Task Description
You are debugging a data corruption issue in a simple in-memory database system. Data seems to get corrupted between operations, and the bug appears to be in the API layer, but the root cause is elsewhere.

## Problem
The database system has three layers:
1. `db.py` - Simple in-memory database using dictionaries
2. `models.py` - Model classes that wrap database operations
3. `api.py` - API layer that uses models for CRUD operations

When performing multiple read-modify-write operations, the database state becomes corrupted. Subsequent reads return wrong data.

## Your Goal
Find and fix the bug so that all tests pass. The corruption manifests in `api.py` but the actual bug is in `db.py`.

## Files
- `src/db.py` - In-memory database implementation
- `src/models.py` - Model classes
- `src/api.py` - API layer
- `tests/test_db.py` - Test suite

## Expected Behavior
Read-modify-write operations should preserve data integrity. All reads should return the last written values, not stale or corrupted data.
