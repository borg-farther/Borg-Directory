#!/bin/bash
# Setup for django__django-15382
# This task requires a Django checkout at commit 770d3e6a4ce8e0a91a9e27156036c1985e74d4a3
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
git checkout 770d3e6a4ce8e0a91a9e27156036c1985e74d4a3 2>/dev/null

# Apply test patch (adds the failing test)
cat > /tmp/test_patch.diff << 'PATCHEOF'
diff --git a/tests/expressions/tests.py b/tests/expressions/tests.py
--- a/tests/expressions/tests.py
+++ b/tests/expressions/tests.py
@@ -1905,6 +1905,13 @@ def test_optimizations(self):
         )
         self.assertNotIn('ORDER BY', captured_sql)
 
+    def test_negated_empty_exists(self):
+        manager = Manager.objects.create()
+        qs = Manager.objects.filter(
+            ~Exists(Manager.objects.none()) & Q(pk=manager.pk)
+        )
+        self.assertSequenceEqual(qs, [manager])
+
 
 class FieldTransformTests(TestCase):
 

PATCHEOF
git apply /tmp/test_patch.diff 2>/dev/null || true

# Install Django in dev mode
pip install -e . -q 2>/dev/null || true

echo "Setup complete for django__django-15382"
