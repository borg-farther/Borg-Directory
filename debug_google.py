import re

p = re.compile(r"\bAIza[A-Za-z0-9_-]{35}\b")

# Compare the debug script key vs the test key
debug_key = "AIza" + "x" * 35
test_key = "AIzaSyabcdefghijklmnopqrstuvwxyz01234567"

print("Debug key: len=%d, suffix_len=%d" % (len(debug_key), len(debug_key)-4))
print("Test key:  len=%d, suffix_len=%d" % (len(test_key), len(test_key)-4))
print()
print("Debug key: %r" % debug_key)
print("Test key:  %r" % test_key)
print()
print("Debug key match: %r" % p.findall(debug_key))
print("Test key match:  %r" % p.findall(test_key))
print()

# Show character-by-character of test key suffix
suffix = test_key[4:]
print("Test key suffix (%d chars): %r" % (len(suffix), suffix))
