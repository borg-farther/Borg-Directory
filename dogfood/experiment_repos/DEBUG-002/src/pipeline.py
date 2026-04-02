"""Data processing pipeline with TypeError bug."""


def get_user_data(user_id):
    """Fetch user data from upstream service - returns None instead of empty dict."""
    users = {
        1: {"name": "Alice", "email": "alice@example.com"},
        2: {"name": "Bob", "email": "bob@example.com"},
    }
    # Bug: returns None instead of {} for missing users
    return users.get(user_id)


def normalize_data(data_list):
    """Normalize a list of user data dicts."""
    result = []
    for item in data_list:
        # This will crash with AttributeError if item is None
        result.append({
            "id": item["id"],
            "name": item["name"].upper(),
            "email": item["email"].lower(),
        })
    return result


def process_users(user_ids):
    """Process a list of users through the pipeline."""
    data_list = [get_user_data(uid) for uid in user_ids]
    # Bug: doesn't handle None values in data_list
    return normalize_data(data_list)


def generate_report(user_ids):
    """Generate a report for given user IDs."""
    processed = process_users(user_ids)
    lines = ["User Report", "=" * 50]
    for user in processed:
        lines.append(f"{user['name']} ({user['email']})")
    return "\n".join(lines)
