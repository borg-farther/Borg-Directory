# PyPI Publishing Checklist for agent-borg

## Pre-Flight Checks

- [x] Version 2.4.0 set in `pyproject.toml`
- [x] Version 2.4.0 set in `borg/__init__.py`
- [x] Package builds cleanly (`python -m build` succeeds)
- [x] Metadata verified in built wheel (name, version, description, URLs, classifiers, dependencies)

## Generate PyPI Token

1. Go to **https://pypi.org/manage/account/token/**
2. Click **"Create a new token"**
3. Select scope: **"Entire account"** (or scope specifically to `agent-borg` if option exists)
4. Token name: `agent-borg-publish` (or similar)
5. Copy the token immediately — it won't be shown again

## Publish to PyPI

### Option A: Using Twine (recommended)

```bash
cd ~/hermes-workspace/borg

# Install twine if not present
pip install twine

# Upload using your token
TWINE_PASSWORD=<your-token-here> twine upload dist/agent_borg-2.4.0-py3-none-any.whl

# Or interactively (will prompt for username/password)
twine upload dist/agent_borg-2.4.0-py3-none-any.whl
# Username: __token__
# Password: pypi-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Option B: Using the token directly

```bash
pip install twine
python -m twine upload --username __token__ --password <your-token-here> dist/agent_borg-2.4.0-py3-none-any.whl
```

## Verify Published Package

1. Go to **https://pypi.org/project/agent-borg/**
2. Confirm version shows **2.4.0**
3. Confirm description, license, and URLs are correct
4. Test installation: `pip install agent-borg==2.4.0`

## Post-Publish Notes

- The old PyPI token (if any) should be deleted from pypi.org/manage/account/token/
- Consider setting up a GitHub Actions workflow for future releases
- Optional: run `pip install agent-borg[all]` to verify extras install correctly

## Optional Cleanup (deprecation warnings)

The build shows warnings about `project.license` as a TOML table (deprecated in setuptools>=77) and "License :: OSI Approved :: MIT License" classifier. To fix these in a future release:

```toml
# In pyproject.toml, change:
license = {text = "MIT"}

# To:
license = "MIT"

# And remove this classifier:
"License :: OSI Approved :: MIT License",
```
