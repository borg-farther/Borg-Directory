"""Flask app with incorrect HTTP status codes."""
from flask import Flask, jsonify, abort, request

app = Flask(__name__)

# In-memory user database
USERS = {
    1: {"id": 1, "name": "Alice"},
    2: {"id": 2, "name": "Bob"},
    3: {"id": 3, "name": "Charlie"},
}


@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user by ID - returns 200 with null instead of 404 when not found."""
    user = USERS.get(user_id)
    # Bug: should abort(404) if user is None
    return jsonify(user)


@app.route("/api/users", methods=["POST"])
def create_user():
    """Create a new user - returns 500 instead of 400 for invalid JSON."""
    # Bug: should try/except and abort(400) for invalid JSON
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name required"}), 400
    return jsonify({"id": 4, "name": data["name"]}), 201


if __name__ == "__main__":
    app.run(debug=True)
