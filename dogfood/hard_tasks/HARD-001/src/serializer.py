"""Serializer layer - transforms database records to API responses."""

def serialize_user(user_record):
    """Transform a database record into API response format.
    
    Expected output format:
    {
        "id": int,
        "name": str,
        "email": str,
        "created_at": str
    }
    """
    if not user_record:
        return None
    
    # Bug is here: db.py uses 'email_addr' and 'signup_date'
    # but this function looks for 'email' and 'created_at'
    return {
        "id": user_record.get("user_id"),
        "name": user_record.get("user_name"),
        "email": user_record.get("email"),  # Should be "email_addr"
        "created_at": user_record.get("created_at")  # Should be "signup_date"
    }
