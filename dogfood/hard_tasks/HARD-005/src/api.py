"""API layer that uses models for CRUD operations."""
from typing import Dict, Optional, List
from models import UserModel, ProductModel
from db import Database, get_db


class UserAPI:
    """High-level API for user operations."""

    def __init__(self, db: Database = None):
        self.db = db or get_db()
        self.model = UserModel(self.db)

    def register_user(self, user_id: str, name: str, email: str, **kwargs) -> Dict:
        """Register a new user."""
        if self.model.exists(user_id):
            raise ValueError(f"User {user_id} already exists")

        return self.model.create(user_id, name, email, **kwargs)

    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user details."""
        return self.model.get(user_id)

    def update_user_email(self, user_id: str, new_email: str) -> Optional[Dict]:
        """Update a user's email address."""
        user = self.model.get(user_id)
        if user is None:
            return None

        # BUG: This mutation corrupts the database because
        # user = self.model.get(user_id) returns a reference
        # to the internal dict, not a copy!
        user["email"] = new_email
        # No need to call db.put - the mutation already affected internal state
        # But for consistency we might call it anyway (which also looks correct but is redundant)

        return user

    def apply_discount(self, user_id: str, discount_percent: float) -> Optional[Dict]:
        """Apply a discount to user's purchase history (simulated)."""
        user = self.model.get(user_id)
        if user is None:
            return None

        # Get current "discount" or initialize
        current_discount = user.get("discount", 0)
        user["discount"] = current_discount + discount_percent

        return user

    def birthday_update(self, user_id: str) -> Optional[Dict]:
        """Update user on their birthday."""
        user = self.model.get(user_id)
        if user is None:
            return None

        user["age"] += 1
        user["last_birthday"] = "2024-01-01"

        return user


class ProductAPI:
    """High-level API for product operations."""

    def __init__(self, db: Database = None):
        self.db = db or get_db()
        self.model = ProductModel(self.db)

    def add_product(self, product_id: str, name: str, price: float) -> Dict:
        """Add a new product."""
        return self.model.create(product_id, name, price)

    def get_product(self, product_id: str) -> Optional[Dict]:
        """Get product details."""
        return self.model.get(product_id)

    def purchase(self, product_id: str, quantity: int) -> Optional[Dict]:
        """Simulate a product purchase."""
        product = self.model.get(product_id)
        if product is None:
            return None

        if product["stock"] < quantity:
            raise ValueError("Insufficient stock")

        # BUG: Same aliasing issue - mutating returned dict corrupts database
        product["stock"] -= quantity
        product["purchases"] = product.get("purchases", 0) + quantity

        return product

    def restock(self, product_id: str, quantity: int) -> Optional[Dict]:
        """Restock a product."""
        return self.model.update_stock(product_id, quantity)
