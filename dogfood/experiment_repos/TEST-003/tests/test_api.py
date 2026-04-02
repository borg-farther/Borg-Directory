"""Tests for REST API - only has 1 smoke test, needs more!"""
import pytest
from src.api import app


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health():
    """Smoke test - just checks health endpoint."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 200
