#!/bin/bash
# Regenerate the supply-chain artifacts (gate #24):
#   requirements-lock.txt — exact runtime dependency pins from a clean install
#   sbom/cyclonedx.json   — CycloneDX SBOM of the installed environment
# Run from the repo root on any dependency or release change, commit both.
set -euo pipefail

CLEAN_ENV="$(mktemp -d)/cleanenv"
TOOL_ENV="$(mktemp -d)/toolenv"

python3 -m venv "$CLEAN_ENV"
"$CLEAN_ENV/bin/pip" install --quiet .
"$CLEAN_ENV/bin/pip" freeze --exclude-editable | grep -v '^agent-borg' > requirements-lock.txt

# The SBOM generator lives in its OWN venv so the tooling never pollutes the SBOM.
python3 -m venv "$TOOL_ENV"
"$TOOL_ENV/bin/pip" install --quiet cyclonedx-bom pip-audit
mkdir -p sbom
"$TOOL_ENV/bin/cyclonedx-py" environment "$CLEAN_ENV" \
  --pyproject pyproject.toml --output-reproducible --of JSON -o sbom/cyclonedx.json

echo "== pip-audit on the lock =="
"$TOOL_ENV/bin/pip-audit" -r requirements-lock.txt

rm -rf build ./*.egg-info
echo "Wrote requirements-lock.txt and sbom/cyclonedx.json"
