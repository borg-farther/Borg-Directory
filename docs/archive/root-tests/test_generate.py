from borg.integrations.mcp_server import _borg_generate_handler, TOOLS

# Test 5: Count tools
print(f'=== TEST 5: Tool count = {len(TOOLS)} ===')
for t in TOOLS:
    print(f'  - {t["name"]}')

# Test 1
print('\n=== TEST 1: pack=systematic-debugging, format=cursorrules ===')
r = _borg_generate_handler(pack='systematic-debugging', format='cursorrules')
is_error = isinstance(r, dict) and r.get('error', False)
print(f'Success: {not is_error}')
content = r.get('content', '') if isinstance(r, dict) else str(r)
print(f'Content length: {len(content)}')
print(f'First 200 chars: {content[:200]}')

# Test 2
print('\n=== TEST 2: pack=systematic-debugging, format=all ===')
r = _borg_generate_handler(pack='systematic-debugging', format='all')
is_error = isinstance(r, dict) and r.get('error', False)
print(f'Success: {not is_error}')
content = r.get('content', '') if isinstance(r, dict) else str(r)
print(f'Content length: {len(content)}')
print(f'First 200 chars: {content[:200]}')

# Test 3
print('\n=== TEST 3: pack=nonexistent, format=cursorrules ===')
r = _borg_generate_handler(pack='nonexistent', format='cursorrules')
is_error = isinstance(r, dict) and r.get('error', False)
print(f'Got error: {is_error}')
print(f'Response: {str(r)[:300]}')

# Test 4
print('\n=== TEST 4: pack=empty, format=cursorrules ===')
r = _borg_generate_handler(pack='', format='cursorrules')
is_error = isinstance(r, dict) and r.get('error', False)
print(f'Got error: {is_error}')
print(f'Response: {str(r)[:300]}')
