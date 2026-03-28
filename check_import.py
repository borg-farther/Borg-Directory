import sys
sys.path.insert(0, '/root/hermes-workspace/guild-v2')
try:
    import borg
    print("OK:", borg.__file__)
except Exception as e:
    print("FAIL:", e)
