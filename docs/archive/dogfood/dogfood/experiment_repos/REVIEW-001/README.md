# REVIEW-001: Python Code with Security Vulnerabilities

## Problem
The `src/auth.py` module has multiple security vulnerabilities:
1. SQL injection in `authenticate_user()` - string formatting in SQL
2. SQL injection in `get_user_profile()` - user_id not parameterized
3. Plaintext password storage - passwords stored without hashing
4. No rate limiting on authentication attempts

## Task
Fix all high-severity security vulnerabilities:
- Use parameterized queries to prevent SQL injection
- Hash passwords with proper algorithm (bcrypt or argon2)
- Add rate limiting to authentication

## Verification
```bash
./check.sh  # bandit should report 0 high-severity issues
```
