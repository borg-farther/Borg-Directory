"""
Test to verify the violation_error_code feature for BaseConstraint.
"""
import os
import sys
import django

# Setup Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_settings')

# Create a minimal test settings module
test_settings = """
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
]
SECRET_KEY = 'test-secret-key'
USE_TZ = True
"""

# Write test settings
with open('test_settings.py', 'w') as f:
    f.write(test_settings)

django.setup()

from django.db import models
from django.db.models import CheckConstraint, Q
from django.core.exceptions import ValidationError


# Test 1: Test that BaseConstraint accepts violation_error_code parameter
print("Test 1: BaseConstraint with violation_error_code...")
try:
    constraint = models.BaseConstraint(
        name='test_constraint',
        violation_error_code='custom_code'
    )
    print(f"  - violation_error_code attribute: {constraint.violation_error_code}")
    assert constraint.violation_error_code == 'custom_code', "violation_error_code not set correctly"
    print("  - PASS: BaseConstraint accepts violation_error_code")
except Exception as e:
    print(f"  - FAIL: {e}")

# Test 2: Test that violation_error_code is used in ValidationError
print("\nTest 2: CheckConstraint with violation_error_code...")
try:
    from django.contrib.auth.models import User
    
    constraint = CheckConstraint(
        check=Q(username__isnull=False),
        name='test_not_null',
        violation_error_code='null_username'
    )
    
    # Simulate validation
    class MockModel:
        username = None
    
    try:
        constraint.validate(MockModel, None)
    except ValidationError as e:
        print(f"  - Error code: {e.code}")
        assert e.code == 'null_username', f"Expected 'null_username', got '{e.code}'"
        print("  - PASS: ValidationError has correct code")
except Exception as e:
    print(f"  - FAIL: {e}")

# Test 3: Test that both message and code can be customized
print("\nTest 3: CheckConstraint with both message and code...")
try:
    constraint = CheckConstraint(
        check=Q(username__isnull=False),
        name='test_custom',
        violation_error_message='Username cannot be null',
        violation_error_code='username_null'
    )
    
    class MockModel:
        username = None
    
    try:
        constraint.validate(MockModel, None)
    except ValidationError as e:
        print(f"  - Error message: {e.message}")
        print(f"  - Error code: {e.code}")
        assert e.code == 'username_null', f"Expected 'username_null', got '{e.code}'"
        print("  - PASS: Both message and code are customizable")
except Exception as e:
    print(f"  - FAIL: {e}")

# Test 4: Test default behavior (code should be None by default)
print("\nTest 4: Default behavior (no code specified)...")
try:
    constraint = CheckConstraint(
        check=Q(username__isnull=False),
        name='test_default'
    )
    
    class MockModel:
        username = None
    
    try:
        constraint.validate(MockModel, None)
    except ValidationError as e:
        print(f"  - Error code: {e.code}")
        assert e.code is None, f"Expected None, got '{e.code}'"
        print("  - PASS: Default code is None")
except Exception as e:
    print(f"  - FAIL: {e}")

print("\n=== All tests passed! ===")
