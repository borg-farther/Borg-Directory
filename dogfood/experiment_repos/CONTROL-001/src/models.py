"""Data models."""
from dataclasses import dataclass


@dataclass
class User:
    """User model."""
    id: int
    name: str
    email: str
