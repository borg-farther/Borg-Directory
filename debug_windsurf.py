from borg.core.generate import generate_rules, load_pack

pack = load_pack("systematic-debugging")
result = generate_rules(pack, "windsurfrules")

print("=== @ANTI_PATTERNS section ===")
start = result.find("@ANTI_PATTERNS")
if start >= 0:
    # Get a chunk after @ANTI_PATTERNS
    chunk = result[start:start+500]
    print(repr(chunk))

print()
print("=== searching for 'NOT:' ===")
idx = 0
count = 0
while True:
    idx = result.find("NOT:", idx)
    if idx < 0 or count > 5:
        break
    print(f"  found NOT: at {idx}: {repr(result[idx:idx+80])}")
    idx += 4
    count += 1

print()
print("Lowercase result has 'do not'?", "do not" in result.lower())
print("Lowercase result has \"don't\"?", "don't" in result.lower())
print("Lowercase result has 'never'?", "never" in result.lower())
print("Lowercase result has 'avoid'?", "avoid" in result.lower())

# Print all unique anti-patterns in windsurfrules
from borg.core.generate import _collect_anti_patterns
phases = pack.get("phases", [])
anti = _collect_anti_patterns(phases)
print(f"\nCollected {len(anti)} anti-patterns:")
for a in anti:
    print(f"  {repr(a)}")
