#!/bin/bash
cd "$(dirname "$0")"

# Run bandit security scan
echo "Running bandit security scan..."
bandit src/auth.py 2>&1 | tee bandit_output.txt

# Check for SQL injection patterns that bandit might miss
echo ""
echo "Checking for SQL injection vulnerability patterns..."
# Look for f-strings with SQL and variable interpolation
SQL_INJECTION_PATTERN=$(grep -nE 'f["\'].*SELECT.*{' src/auth.py 2>/dev/null || true)

if [ -n "$SQL_INJECTION_PATTERN" ]; then
    echo "FAIL: Found SQL injection vulnerability pattern:"
    echo "$SQL_INJECTION_PATTERN"
    exit 1
fi

# Check for plaintext password storage
echo ""
echo "Checking for plaintext password storage..."
PLAIN_TEXT=$(grep -n 'password.*='"'"'" src/auth.py 2>/dev/null || grep -n 'password.*=.*"' src/auth.py 2>/dev/null || true)

# Filter out bcrypt/argon2 usage which is safe
if [ -n "$PLAIN_TEXT" ] && ! echo "$PLAIN_TEXT" | grep -q "hashpw\|bcrypt\|argon2\|hash_password"; then
    echo "WARNING: Possible plaintext password storage:"
    echo "$PLAIN_TEXT"
fi

# Run pytest
echo ""
echo "Running pytest..."
python -m pytest tests/test_auth.py -v
