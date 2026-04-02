# Solution: REST API Integration Tests

## Required Tests (8+)

```python
def test_health(client):
    """Smoke test - health endpoint."""
    response = client.get('/health')
    assert response.status_code == 200


def test_get_items_empty(client):
    """GET /items when empty."""
    response = client.get('/items')
    assert response.status_code == 200
    assert response.json == []


def test_create_item(client):
    """POST /items - create item."""
    response = client.post('/items', json={'name': 'Test Item'})
    assert response.status_code == 201
    assert response.json['name'] == 'Test Item'
    assert 'id' in response.json


def test_create_item_missing_name(client):
    """POST /items - missing name returns 400."""
    response = client.post('/items', json={})
    assert response.status_code == 400
    assert 'error' in response.json


def test_get_item(client):
    """GET /items/<id> - get created item."""
    client.post('/items', json={'name': 'Test'})
    response = client.get('/items/1')
    assert response.status_code == 200
    assert response.json['name'] == 'Test'


def test_get_item_not_found(client):
    """GET /items/<id> - not found returns 404."""
    response = client.get('/items/999')
    assert response.status_code == 404


def test_update_item(client):
    """PUT /items/<id> - update item."""
    client.post('/items', json={'name': 'Original'})
    response = client.put('/items/1', json={'name': 'Updated'})
    assert response.status_code == 200
    assert response.json['name'] == 'Updated'


def test_update_item_not_found(client):
    """PUT /items/<id> - not found returns 404."""
    response = client.put('/items/999', json={'name': 'Updated'})
    assert response.status_code == 404


def test_delete_item(client):
    """DELETE /items/<id> - delete item."""
    client.post('/items', json={'name': 'ToDelete'})
    response = client.delete('/items/1')
    assert response.status_code == 200


def test_delete_item_not_found(client):
    """DELETE /items/<id> - not found returns 404."""
    response = client.delete('/items/999')
    assert response.status_code == 404
```

## Verification
```bash
./check.sh  # Should pass with 8+ tests
```
