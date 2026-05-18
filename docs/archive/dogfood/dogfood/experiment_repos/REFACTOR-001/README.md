# REFACTOR-001: Duplicate Code in Reports

## Task Description
The `src/reports.py` file has three report generation functions (`generate_user_report`, `generate_sales_report`, `generate_inventory_report`) that share ~80% identical code for:
- Report header (border, title, timestamp)
- Report footer (totals, end marker)
- Item formatting with dashed separators

## Your Task
Refactor the code to extract common code into shared helper functions. The tests must still pass, and pylint should not report duplicate code violations.

## Files
- `src/reports.py` - Has duplicated code
- `tests/test_reports.py` - Tests that verify report generation still works
- `check.sh` - Runs tests AND pylint to check for duplicate code
