"""Tests for Flask app status codes."""
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_get_existing_user_returns_200(client):
    """Existing user should return 200."""
    response = client.get("/api/users/1")
    assert response.status_code == 200
    assert response.json["name"] == "Alice"


def test_get_missing_user_returns_404(client):
    """Missing user should return 404, not 200 with null."""
    response = client.get("/api/users/999")
    assert response.status_code == 404


def test_create_user_valid_json_returns_201(client):
    """Valid JSON should return 201."""
    response = client.post("/api/users", json={"name": "Dave"})
    assert response.status_code == 201


def test_create_user_missing_name_returns_400(client):
    """Missing name should return 400."""
    response = client.post("/api/users", json={})
    assert response.status_code == 400


def test_create_user_invalid_json_returns_400(client):
    """Invalid JSON should return 400, not 500."""
    response = client.post(
        "/api/users",
        data="not valid json",
        content_type="application/json"
    )
    assert response.status_code == 400
