#!/usr/bin/env bash
# Install Borg's pre-commit hooks into your local clone.
# Run once after cloning, or after pulling updates that change .githooks/.
set -e
cd "$(git rev-parse --show-toplevel)"

if [ ! -d .githooks ]; then
  echo "ERROR: .githooks/ directory not found. Are you in the Borg repo?"
  exit 1
fi

git config core.hooksPath .githooks
echo "✓ Hooks path set to .githooks/"
echo "✓ Pre-commit hook will run on next 'git commit'"
echo ""
echo "Verify with: bash .githooks/pre-commit && echo HOOK_OK"
