# REVIEW-002: Python Code with Performance Issues

## Problem
The `src/search.py` module has O(n²) performance issues:
1. `search_items_nested()` uses nested loops to search - O(n²)
2. `load_and_search_file()` loads entire file into memory then uses nested loops

## Task
Fix the performance issues:
1. Replace nested loops with dict lookup - O(n) to O(1)
2. Use streaming for file reads instead of loading entire file

## Verification
```bash
./check.sh
```
