"""Model classes that wrap database operations."""
from typing import Dict, Optional, Any, List
from db import Database, get_db


class UserModel:
    """User model with database operations."""

    def __init__(self, db: Database = None):
        self.db = db or get_db()

    def create(self, user_id: str, name: str, email: str, age: int = 0) -> Dict:
        """Create a new user."""
        user_data = {
            "id": user_id,
            "name": name,
            "email": email,
            "age": age,
        }
        self.db.put(user_id, user_data)
        return user_data

    def get(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID."""
        return self.db.get(user_id)

    def update(self, user_id: str, **kwargs) -> Optional[Dict]:
        """Update user fields."""
        user = self.db.get(user_id)
        if user is None:
            return None

        for key, value in kwargs.items():
            user[key] = value

        self.db.put(user_id, user)
        return user

    def delete(self, user_id: str) -> bool:
        """Delete a user."""
        return self.db.delete(user_id)

    def exists(self, user_id: str) -> bool:
        """Check if user exists."""
        return self.db.exists(user_id)

    def increment_age(self, user_id: str) -> Optional[Dict]:
        """Increment a user's age by 1."""
        user = self.db.get(user_id)
        if user is None:
            return None

        user["age"] += 1
        self.db.put(user_id, user)
        return user


class ProductModel:
    """Product model with database operations."""

    def __init__(self, db: Database = None):
        self.db = db or get_db()

    def create(self, product_id: str, name: str, price: float, stock: int = 0) -> Dict:
        """Create a new product."""
        product_data = {
            "id": product_id,
            "name": name,
            "price": price,
            "stock": stock,
        }
        self.db.put(product_id, product_data)
        return product_data

    def get(self, product_id: str) -> Optional[Dict]:
        """Get a product by ID."""
        return self.db.get(product_id)

    def update_stock(self, product_id: str, quantity: int) -> Optional[Dict]:
        """Update product stock level."""
        product = self.db.get(product_id)
        if product is None:
            return None

        product["stock"] += quantity
        self.db.put(product_id, product)
        return product

    def delete(self, product_id: str) -> bool:
        """Delete a product."""
        return self.db.delete(product_id)
