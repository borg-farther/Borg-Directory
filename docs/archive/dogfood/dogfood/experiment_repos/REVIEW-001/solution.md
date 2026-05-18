# Solution: Security Vulnerabilities Fix

## The Problems

1. **SQL Injection** via string formatting:
```python
query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
```

2. **Plaintext passwords**:
```python
query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
```

## The Fix

### 1. Parameterized Queries
```python
def authenticate_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    # SAFE: Parameterized query
    query = "SELECT * FROM users WHERE username = ? AND password = ?"
    cursor.execute(query, (username, password))

    result = cursor.fetchone()
    conn.close()

    if result:
        return {'username': result[1], 'id': result[0]}
    return None
```

### 2. Password Hashing
```python
import bcrypt

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def authenticate_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()

    query = "SELECT * FROM users WHERE username = ?"
    cursor.execute(query, (username,))

    result = cursor.fetchone()
    conn.close()

    if result and verify_password(password, result[2]):
        return {'username': result[1], 'id': result[0]}
    return None
```

### Key Changes
1. Use `?` placeholders and pass values as tuple
2. Use bcrypt for password hashing
3. Use parameterized query for user_id in get_user_profile
