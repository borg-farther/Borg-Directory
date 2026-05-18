# Solution for HARD-001

## Root Cause
The bug is in `src/serializer.py` in the `serialize_user()` function.

The database layer (`db.py`) returns records with these keys:
- `user_id`
- `user_name`
- `email_addr` (NOT `email`)
- `signup_date` (NOT `created_at`)

The serializer was looking for `email` and `created_at` which don't exist in the database record, so these fields came back as `None`.

## Fix
In `src/serializer.py`, change the `serialize_user()` function to use the correct database field names:

```python
return {
    "id": user_record.get("user_id"),
    "name": user_record.get("user_name"),
    "email": user_record.get("email_addr"),  # Changed from "email"
    "created_at": user_record.get("signup_date")  # Changed from "created_at"
}
```

## Why This Was Tricky
1. The error **manifests** in the API response (missing/None values for email and created_at)
2. The bug **originates** in the serializer which incorrectly maps field names
3. The db.py file uses non-standard field names (`email_addr`, `signup_date`) which is a red herring - it looks like the API should use standard names but the serializer must adapt to the db layer's naming convention
EOF; __hermes_rc=$?; printf '__HERMES_FENCE_a9f7b3__'; exit $__hermes_rc
