"""Flask API layer - handles HTTP requests."""

from flask import Flask, jsonify
from .db import get_user_by_id
from .serializer import serialize_user

app = Flask(__name__)

@app.route("/api/user/<int:user_id>")
def get_user(user_id):
    """Return user profile data."""
    user_record = get_user_by_id(user_id)
    if not user_record:
        return jsonify({"error": "User not found"}), 404
    
    serialized = serialize_user(user_record)
    return jsonify(serialized)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})
