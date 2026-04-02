#!/bin/bash
# Setup for django__django-11728
# This task requires a Django checkout at commit 05457817647368be4b019314fcc655445a5b4c0c
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
git checkout 05457817647368be4b019314fcc655445a5b4c0c 2>/dev/null

# Apply test patch (adds the failing test)
cat > /tmp/test_patch.diff << 'PATCHEOF'
diff --git a/tests/admin_docs/test_views.py b/tests/admin_docs/test_views.py
--- a/tests/admin_docs/test_views.py
+++ b/tests/admin_docs/test_views.py
@@ -348,9 +348,13 @@ def test_simplify_regex(self):
             (r'^a', '/a'),
             (r'^(?P<a>\w+)/b/(?P<c>\w+)/$', '/<a>/b/<c>/'),
             (r'^(?P<a>\w+)/b/(?P<c>\w+)$', '/<a>/b/<c>'),
+            (r'^(?P<a>\w+)/b/(?P<c>\w+)', '/<a>/b/<c>'),
             (r'^(?P<a>\w+)/b/(\w+)$', '/<a>/b/<var>'),
+            (r'^(?P<a>\w+)/b/(\w+)', '/<a>/b/<var>'),
             (r'^(?P<a>\w+)/b/((x|y)\w+)$', '/<a>/b/<var>'),
+            (r'^(?P<a>\w+)/b/((x|y)\w+)', '/<a>/b/<var>'),
             (r'^(?P<a>(x|y))/b/(?P<c>\w+)$', '/<a>/b/<c>'),
+            (r'^(?P<a>(x|y))/b/(?P<c>\w+)', '/<a>/b/<c>'),
             (r'^(?P<a>(x|y))/b/(?P<c>\w+)ab', '/<a>/b/<c>ab'),
             (r'^(?P<a>(x|y)(\(|\)))/b/(?P<c>\w+)ab', '/<a>/b/<c>ab'),
             (r'^a/?$', '/a/'),

PATCHEOF
git apply /tmp/test_patch.diff 2>/dev/null || true

# Install Django in dev mode
pip install -e . -q 2>/dev/null || true

echo "Setup complete for django__django-11728"
