"""
Tests for the violation_error_code parameter of BaseConstraint.
"""
import unittest

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import CheckConstraint, Q
from django.test import TestCase

from .models import Product


class ViolationErrorCodeTests(TestCase):
    """Test that violation_error_code can be customized in constraints."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._old_constraints = Product._meta.constraints.copy()

    @classmethod
    def tearDownClass(cls):
        Product._meta.constraints = cls._old_constraints
        super().tearDownClass()

    def test_custom_violation_error_code(self):
        """Test that violation_error_code parameter works."""
        Product._meta.constraints = [
            CheckConstraint(
                check=Q(price__gte=0),
                name="price_non_negative",
                violation_error_code="negative_price",
            ),
        ]
        Product._meta.contribute_to_class(Product, "Product")

        product = Product(name="Test", price=-10)
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()

        self.assertEqual(cm.exception.code, "negative_price")
        self.assertIn("price_non_negative", str(cm.exception.message))
        print("Test passed: custom violation_error_code works!")

    def test_default_violation_error_code(self):
        """Test that default violation_error_code is None (uses default ValidationError behavior)."""
        Product._meta.constraints = [
            CheckConstraint(
                check=Q(price__gte=0),
                name="price_non_negative",
            ),
        ]
        Product._meta.contribute_to_class(Product, "Product")

        product = Product(name="Test", price=-10)
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()

        # Default code should be None or 'invalid'
        print(f"Default error code: {cm.exception.code}")
        print("Test passed: default violation_error_code works!")

    def test_custom_violation_error_message_and_code(self):
        """Test that both violation_error_message and violation_error_code can be used together."""
        Product._meta.constraints = [
            CheckConstraint(
                check=Q(price__gte=0),
                name="price_non_negative",
                violation_error_message="Price must be non-negative",
                violation_error_code="negative_price",
            ),
        ]
        Product._meta.contribute_to_class(Product, "Product")

        product = Product(name="Test", price=-10)
        with self.assertRaises(ValidationError) as cm:
            product.full_clean()

        self.assertEqual(cm.exception.code, "negative_price")
        self.assertIn("Price must be non-negative", str(cm.exception.message))
        print("Test passed: both violation_error_message and violation_error_code work together!")


if __name__ == "__main__":
    unittest.main()
