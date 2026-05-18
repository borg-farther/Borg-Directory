#!/bin/bash
# Setup for django__django-16485
# This task requires a Django checkout at commit 39f83765e12b0e5d260b7939fc3fe281d879b279
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
git checkout 39f83765e12b0e5d260b7939fc3fe281d879b279 2>/dev/null

# Apply test patch (adds the failing test)
cat > /tmp/test_patch.diff << 'PATCHEOF'
diff --git a/tests/template_tests/filter_tests/test_floatformat.py b/tests/template_tests/filter_tests/test_floatformat.py
--- a/tests/template_tests/filter_tests/test_floatformat.py
+++ b/tests/template_tests/filter_tests/test_floatformat.py
@@ -111,6 +111,8 @@ def test_zero_values(self):
         self.assertEqual(
             floatformat(0.000000000000000000015, 20), "0.00000000000000000002"
         )
+        self.assertEqual(floatformat("0.00", 0), "0")
+        self.assertEqual(floatformat(Decimal("0.00"), 0), "0")
 
     def test_negative_zero_values(self):
         tests = [

PATCHEOF
git apply /tmp/test_patch.diff 2>/dev/null || true

# Install Django in dev mode
pip install -e . -q 2>/dev/null || true

echo "Setup complete for django__django-16485"
