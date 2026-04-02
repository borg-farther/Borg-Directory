# Solution for DEBUG-001

## Bug Description
The Flask app returns incorrect HTTP status codes:
1. `/api/users/<id>` returns `200` with `null` when user not found (should be `404`)
2. `POST /api/users` with invalid JSON returns `500` (should be `400`)

## Fix

In `src/app.py`, modify the `get_user` function to abort with 404 when user is None:

```python
@app.route("/api/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    user = USERS.get(user_id)
    if user is None:
        abort(404)
    return jsonify(user)
```

And modify `create_user` to handle invalid JSON with try/except:

```python
@app.route("/api/users", methods=["POST"])
def create_user():
    try:
        data = request.get_json()
    except Exception:
        abort(400)
    if not data or "name" not in data:
        return jsonify({"error": "name required"}), 400
    return jsonify({"id": 4, "name": data["name"]}), 201
```
