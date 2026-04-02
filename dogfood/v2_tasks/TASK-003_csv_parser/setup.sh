#!/bin/bash
cd "$(dirname "$0")"
mkdir -p repo
cat > repo/parser.py << 'PYEOF'
def parse_csv(text):
    """Parse CSV text into list of rows. Handles quoted fields."""
    rows = []
    current_row = []
    current_field = ""
    in_quotes = False
    
    for char in text:
        if char == '"':
            in_quotes = not in_quotes
        elif char == ',' and not in_quotes:
            current_row.append(current_field)
            current_field = ""
        elif char == '\n' and not in_quotes:
            current_row.append(current_field)
            rows.append(current_row)
            current_row = []
            current_field = ""
        else:
            current_field += char
    
    # BUG: doesn't handle last field/row if file doesn't end with newline
    # Also: doesn't handle escaped quotes (doubled quotes inside quoted fields)
    
    return rows
PYEOF

cat > repo/test_parser.py << 'PYEOF'
import sys
sys.path.insert(0, '.')
from parser import parse_csv

def test_basic():
    result = parse_csv("a,b,c\n1,2,3\n")
    assert result == [["a","b","c"],["1","2","3"]], f"Basic failed: {result}"

def test_quoted_comma():
    result = parse_csv('name,desc\n"Smith, John","has a, comma"\n')
    assert result == [["name","desc"],["Smith, John","has a, comma"]], f"Quoted comma failed: {result}"

def test_no_trailing_newline():
    result = parse_csv("a,b\n1,2")
    assert result == [["a","b"],["1","2"]], f"No trailing newline failed: {result}"

def test_escaped_quotes():
    result = parse_csv('val\n"he said ""hello"""\n')
    assert result == [["val"],['he said "hello"']], f"Escaped quotes failed: {result}"

def test_empty_fields():
    result = parse_csv("a,,c\n,2,\n")
    assert result == [["a","","c"],["","2",""]], f"Empty fields failed: {result}"

if __name__ == "__main__":
    tests = [test_basic, test_quoted_comma, test_no_trailing_newline, test_escaped_quotes, test_empty_fields]
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            sys.exit(1)
    print("ALL TESTS PASSED")
PYEOF
