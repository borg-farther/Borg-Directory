from datetime import datetime
result = datetime.fromisoformat('2020-01-15T00:00:00Z')
print(f'with Z: {result}, tzinfo={result.tzinfo}')
result2 = datetime.fromisoformat('2020-01-15T00:00:00')
print(f'without Z: {result2}, tzinfo={result2.tzinfo}')
