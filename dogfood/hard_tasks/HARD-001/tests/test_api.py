"""Tests for the User Profile API."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.api import app

client = app.test_client()

def test_user_1_complete_response():
    """User 1 should have all fields correctly populated."""
    response = client.get("/api/user/1")
    assert response.status_code == 200
    data = response.get_json()
    
    assert data["id"] == 1, f"Expected id=1, got {data.get('id')}"
    assert data["name"] == "Alice Smith", f"Expected name='Alice Smith', got {data.get('name')}"
    assert data["email"] == "alice@example.com", f"Expected email='alice@example.com', got {data.get('email')}"
    assert data["created_at"] == "2024-01-15T10:30:00Z", f"Expected created_at, got {data.get('created_at')}"

def test_user_2_complete_response():
    """User 2 should have all fields correctly populated."""
    response = client.get("/api/user/2")
    assert response.status_code == 200
    data = response.get_json()
    
    assert data["id"] == 2, f"Expected id=2, got {data.get('id')}"
    assert data["name"] == "Bob Jones", f"Expected name='Bob Jones', got {data.get('name')}"
    assert data["email"] == "bob@example.com", f"Expected email='bob@example.com', got {data.get('email')}"
    assert data["created_at"] == "2024-02-20T14:45:00Z", f"Expected created_at, got {data.get('created_at')}"

def test_health_endpoint():
    """Health check should return ok status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
