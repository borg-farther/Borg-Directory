# REFACTOR-002: Callback Hell → Async/Await

## Problem
The `src/fetcher.py` module has deeply nested callbacks making it hard to read and maintain.
The `fetch_multiple_urls_callbacks` function has callbacks nested 3+ levels deep.

## Task
Refactor the code to use `async/await` syntax:
1. Convert `fetch_url_callback` to async `fetch_url`
2. Convert `fetch_multiple_urls_callbacks` to async `fetch_multiple_urls`
3. Remove nested callbacks
4. Tests must still pass
5. Maximum callback nesting depth must be <= 2

## Verification
```bash
./check.sh
```
