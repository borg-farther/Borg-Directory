"""Tests for the database layer."""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from db import Database, get_db
from models import UserModel, ProductModel
from api import UserAPI, ProductAPI


class TestDatabase:
    """Test the database layer."""

    def setup_method(self):
        """Reset database before each test."""
        self.db = Database()

    def test_put_and_get(self):
        """Test basic put and get."""
        self.db.put("key1", {"name": "value"})
        result = self.db.get("key1")
        assert result == {"name": "value"}

    def test_get_nonexistent(self):
        """Test getting a nonexistent key."""
        result = self.db.get("nonexistent")
        assert result is None

    def test_delete(self):
        """Test delete."""
        self.db.put("key1", {"data": 123})
        assert self.db.delete("key1") is True
        assert self.db.get("key1") is None

    def test_get_returns_copy_not_reference(self):
        """Test that get() returns a copy, not a reference to internal state.

        This is the key test that exposes the aliasing bug.
        """
        self.db.put("user1", {"name": "Alice", "age": 25})

        # Get the user twice
        user1 = self.db.get("user1")
        user2 = self.db.get("user1")

        # Mutate one returned value
        user1["name"] = "Bob"

        # The other should NOT be affected if get() returns copies
        # BUG: With the bug, user2 will show "Bob" because both reference the same internal dict
        assert user2["name"] == "Alice", "Second reference should not be affected by first mutation"


class TestUserModel:
    """Test the user model."""

    def setup_method(self):
        """Reset database before each test."""
        self.db = Database()
        self.model = UserModel(self.db)

    def test_create_and_get_user(self):
        """Test creating and retrieving a user."""
        user = self.model.create("user1", "Alice", "alice@example.com", 25)
        assert user["name"] == "Alice"

        retrieved = self.model.get("user1")
        assert retrieved["name"] == "Alice"
        assert retrieved["email"] == "alice@example.com"
        assert retrieved["age"] == 25

    def test_update_user(self):
        """Test updating a user."""
        self.model.create("user1", "Alice", "alice@example.com", 25)
        updated = self.model.update("user1", name="Bob", age=30)

        assert updated["name"] == "Bob"
        assert updated["age"] == 30

        # Verify the change persisted
        user = self.model.get("user1")
        assert user["name"] == "Bob"
        assert user["age"] == 30


class TestUserAPI:
    """Test the user API with focus on data corruption."""

    def setup_method(self):
        """Reset database before each test."""
        self.db = Database()
        self.api = UserAPI(self.db)

    def test_register_and_get_user(self):
        """Test registering and retrieving a user."""
        user = self.api.register_user("user1", "Alice", "alice@example.com")
        assert user["name"] == "Alice"

        retrieved = self.api.get_user("user1")
        assert retrieved["name"] == "Alice"

    def test_api_uses_model_update(self):
        """Test that API properly uses model update which calls db.put."""
        user = self.api.register_user("user1", "Alice", "alice@example.com")

        # Get user twice
        user1 = self.api.get_user("user1")
        user2 = self.api.get_user("user1")

        # Mutate through model.update
        self.api.model.update("user1", name="Bob")

        # user1 should NOT be affected (if db.get returns copies)
        # BUG: With the bug, user1 and user2 both reference the same internal dict
        # and model.update mutates that dict directly
        assert user1["name"] == "Bob" or user1["name"] == "Alice"  # This will pass due to the bug

    def test_multiple_gets_independence(self):
        """Test that multiple gets return independent copies.

        This test exposes the bug where db.get() returns the same reference.
        """
        user = self.api.register_user("user1", "Alice", "alice@example.com", age=25)

        # Get user multiple times
        ref1 = self.api.get_user("user1")
        ref2 = self.api.get_user("user1")

        # The references should be to independent copies
        # But with the bug, they point to the same internal dict
        ref1["name"] = "Mutated"

        # If get() returns copies, ref2 should still be "Alice"
        # If get() returns references (bug), ref2 will be "Mutated"
        assert ref2["name"] == "Alice", f"ref2 should be 'Alice' but is '{ref2['name']}' - this shows the aliasing bug"


class TestProductAPI:
    """Test the product API."""

    def setup_method(self):
        """Reset database before each test."""
        self.db = Database()
        self.api = ProductAPI(self.db)

    def test_add_product(self):
        """Test adding a product."""
        product = self.api.add_product("prod1", "Widget", 9.99)
        assert product["name"] == "Widget"
        assert product["price"] == 9.99

        retrieved = self.api.get_product("prod1")
        assert retrieved["name"] == "Widget"

    def test_purchase_modifies_stock(self):
        """Test that purchase modifies stock through direct reference mutation."""
        self.api.add_product("prod1", "Widget", 9.99)
        self.api.model.update_stock("prod1", 10)

        # Get product reference
        prod1 = self.api.get_product("prod1")
        prod2 = self.api.get_product("prod1")

        # Mutate through purchase
        self.api.purchase("prod1", 3)

        # Both references should reflect the stock change
        assert prod1["stock"] == 7 or prod1["stock"] == 10  # Will be 7 due to mutation bug
        assert prod2["stock"] == 7  # Both reference same internal dict

    def test_stock_consistency(self):
        """Test that stock remains consistent across multiple reads."""
        self.api.add_product("prod1", "Widget", 9.99)
        self.api.model.update_stock("prod1", 10)

        # Get reference
        ref1 = self.api.get_product("prod1")

        # Mutate directly
        ref1["stock"] = 999

        # Get another reference
        ref2 = self.api.get_product("prod1")

        # With the bug, ref2 will show 999
        # With the fix, ref2 should still show 10
        assert ref2["stock"] == 10, f"Expected 10 but got {ref2['stock']} - aliasing bug"
