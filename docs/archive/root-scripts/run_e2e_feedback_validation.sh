#!/bin/bash
# E2E feedback loop validation runner — one-shot cron
cd /root/hermes-workspace/borg
HERMES_HOME=/root/.hermes python3 e2e_feedback_validation.py 2>&1
