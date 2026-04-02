"""Simple REST API for items using Flask."""
from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory storage
items = {}
next_id = 1


@app.route('/items', methods=['GET'])
def get_items():
    """Get all items."""
    return jsonify(list(items.values()))


@app.route('/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """Get a single item by ID."""
    if item_id not in items:
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(items[item_id])


@app.route('/items', methods=['POST'])
def create_item():
    """Create a new item."""
    global next_id
    data = request.get_json()

    if not data or 'name' not in data:
        return jsonify({'error': 'Name is required'}), 400

    item = {
        'id': next_id,
        'name': data['name'],
        'description': data.get('description', '')
    }
    items[next_id] = item
    next_id += 1

    return jsonify(item), 201


@app.route('/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an existing item."""
    if item_id not in items:
        return jsonify({'error': 'Item not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    items[item_id]['name'] = data.get('name', items[item_id]['name'])
    items[item_id]['description'] = data.get('description', items[item_id]['description'])

    return jsonify(items[item_id])


@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an item."""
    if item_id not in items:
        return jsonify({'error': 'Item not found'}), 404

    del items[item_id]
    return jsonify({'message': 'Deleted'}), 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok'})


if __name__ == '__main__':
    app.run(debug=True)
