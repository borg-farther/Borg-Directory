"""Data models with nested objects."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class Address:
    """Address model."""
    street: str
    city: str
    country: str
    postal_code: str = ""


@dataclass
class Person:
    """Person model with nested objects."""
    name: str
    email: str
    birth_date: datetime
    address: Optional[Address] = None


@dataclass
class Company:
    """Company model."""
    name: str
    founded_date: datetime
    employees: List[Person] = field(default_factory=list)
    headquarters: Optional[Address] = None


@dataclass
class Event:
    """Event with timestamp."""
    title: str
    event_date: datetime
    created_at: datetime = field(default_factory=datetime.now)
