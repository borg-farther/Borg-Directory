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
