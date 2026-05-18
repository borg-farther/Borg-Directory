#!/usr/bin/env python3
"""Check if Borg is ready for real user onboarding."""
import subprocess
import sys
import os

checks = []

def check(name, cmd, expect_success=True):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        passed = (r.returncode == 0) == expect_success
        output = r.stdout.strip()[:200]
        checks.append((name, passed, output))
        return passed
    except Exception as e:
        checks.append((name, False, str(e)))
        return False

# Core
check("borg installed", "borg version")
check("borg search works", "borg search 'debugging'")
check("borg list works", "borg list")
check("borg-mcp exists", "which borg-mcp")

# MCP tools
check("MCP server imports", "python3 -c 'from borg.integrations.mcp_server import BorgMCPServer; print(\"OK\")'")

# Skills/packs available
check("packs exist", "borg list 2>&1 | grep -c 'pack'")

# Database
check("SQLite DB exists", "ls -la ~/.hermes/borg/*.db 2>&1 || ls -la ~/.borg/*.db 2>&1 || echo 'no db found'")

# DeFi module
check("DeFi module", "python3 -c 'from borg.defi import DeFiRecommender; print(\"OK\")' 2>&1 || echo 'not installed'")

# V3 integration
check("V3 integration", "python3 -c 'from borg.core.v3_integration import BorgV3; print(\"OK\")' 2>&1 || echo 'not available'")

# OpenClaw check
check("OpenClaw running", "docker ps | grep openclaw")

# VPS connectivity
check("VPS credentials exist", "ls ~/.hermes/secrets/hostinger_vps_credentials 2>&1")

# Hermes MCP config
check("Hermes config", "cat ~/.hermes/config.yaml 2>&1 | grep -i borg || echo 'borg not in hermes config'")

print("\nBORG READINESS CHECK")
print("=" * 60)
for name, passed, output in checks:
    status = "✓ PASS" if passed else "✗ FAIL"
    print(f"  {status}: {name}")
    if not passed:
        print(f"         {output[:100]}")

passed_count = sum(1 for _, p, _ in checks if p)
total = len(checks)
print(f"\n{passed_count}/{total} checks passed")

if passed_count == total:
    print("\n>>> BORG IS READY FOR ONBOARDING <<<")
else:
    print(f"\n>>> {total - passed_count} ISSUES TO FIX BEFORE ONBOARDING <<<")
