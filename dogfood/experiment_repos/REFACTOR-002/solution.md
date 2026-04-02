# Solution: Callback Hell → Async/Await

## The Problem
Nested callbacks:
```python
def on_url_fetched(err, data):
    # ...
    if index + 1 < len(urls):
        def on_next_url_fetched(err2, data2):
            # ...
            if index + 2 < len(urls):
                def on_next_next_url_fetched(err3, data3):
                    # ... deeply nested
```

## The Fix

### Async version:
```python
import asyncio

async def fetch_url(url):
    """Async fetch URL."""
    await asyncio.sleep(0.01)  # Simulate async operation
    if url.startswith('http'):
        return f'Data from {url}'
    else:
        raise ValueError(f'Invalid URL: {url}')


async def fetch_multiple_urls(urls):
    """Fetch multiple URLs using asyncio.gather."""
    results = []
    errors = []

    async def fetch_one(url):
        try:
            data = await fetch_url(url)
            return {'url': url, 'data': data}
        except Exception as e:
            return {'url': url, 'error': str(e)}

    # Fetch all concurrently
    tasks = [fetch_one(url) for url in urls]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    for outcome in outcomes:
        if isinstance(outcome, Exception):
            errors.append({'error': str(outcome)})
        else:
            results.append(outcome)

    return results, errors
```

### Key Changes
1. Use `async def` for async functions
2. Use `await` instead of callbacks
3. Use `asyncio.gather()` for concurrent fetching
4. Clean, flat code structure
