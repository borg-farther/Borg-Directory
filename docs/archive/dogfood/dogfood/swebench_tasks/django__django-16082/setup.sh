#!/bin/bash
# Setup for django__django-16082
# This task requires a Django checkout at commit bf47c719719d0e190a99fa2e7f959d5bbb7caf8a
cd "$(dirname "$0")"

# Check if workspace already exists
if [ -d "/workspace/django" ]; then
    echo "Workspace exists"
    exit 0
fi

# Clone Django at the right commit
mkdir -p /workspace
cd /workspace
git clone --depth 100 https://github.com/django/django.git django 2>/dev/null || true
cd django
git checkout bf47c719719d0e190a99fa2e7f959d5bbb7caf8a 2>/dev/null

# Apply test patch (adds the failing test)
cat > /tmp/test_patch.diff << 'PATCHEOF'
diff --git a/tests/expressions/tests.py b/tests/expressions/tests.py
--- a/tests/expressions/tests.py
+++ b/tests/expressions/tests.py
@@ -2416,7 +2416,13 @@ def test_resolve_output_field_number(self):
             (IntegerField, FloatField, FloatField),
             (FloatField, IntegerField, FloatField),
         ]
-        connectors = [Combinable.ADD, Combinable.SUB, Combinable.MUL, Combinable.DIV]
+        connectors = [
+            Combinable.ADD,
+            Combinable.SUB,
+            Combinable.MUL,
+            Combinable.DIV,
+            Combinable.MOD,
+        ]
         for lhs, rhs, combined in tests:
             for connector in connectors:
                 with self.subTest(

PATCHEOF
git apply /tmp/test_patch.diff 2>/dev/null || true

# Install Django in dev mode
pip install -e . -q 2>/dev/null || true

echo "Setup complete for django__django-16082"
