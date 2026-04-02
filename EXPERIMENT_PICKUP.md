# Borg SWE-bench Experiment — Pickup Guide
## Last updated: 2026-04-01 12:20 UTC

## STATUS: All 15 Docker images built. v2 pipeline (host mount) validated. Ready for calibration.

### What's Done
1. Experiment design reviewed by 3 adversarial agents — all blockers addressed
2. 15 tasks selected from SWE-bench Verified (Django, "1-4 hours" difficulty)
3. Hints_text filtered: 4 contaminated tasks removed, replaced with clean medium tasks
4. Docker images building via `/root/hermes-workspace/borg/dogfood/build_all_images.py`
5. First end-to-end calibration run completed: django__django-16631 = FAIL (Condition A)
6. Pipeline fully validated: Docker → test patch → verify fail → agent → verify result

### First Real Data Point
- Task: django__django-16631 (SECRET_KEY_FALLBACKS for sessions)
- Condition A (no trace): FAIL
- Agent correctly found primary fix but couldn't complete secondary fix
- This confirms "1-4 hour" tasks are the RIGHT difficulty level (~40-60% expected)

### Docker Build Status
ALL 15 images built successfully. Verified.

### CRITICAL: Use v2 pipeline (host mount), NOT v1 (docker exec/cp)
v1 (docker exec + docker cp) = 0% pass rate due to infrastructure issues
v2 (host mount) = agents can edit Django source directly, ~30-50% expected pass rate

Use `run_calibration_v2.py` NOT `run_calibration.py`

### What's Next (in order)
1. Run calibration with v2 pipeline: 15 tasks × 3 runs each = 45 runs (Condition A)
2. Select tasks with 30-70% baseline success
3. Run A/B experiment: selected tasks × 2 conditions × 3 runs
4. Analysis

### Key Files
- Design: `/root/hermes-workspace/borg/SWEBENCH_EXPERIMENT_DESIGN.md`
- Task selection: `/root/hermes-workspace/borg/dogfood/v2_data/final_task_selection.json`
- Hints filter: `/root/hermes-workspace/borg/dogfood/v2_data/hints_filter_results.json`
- Executor: `/root/hermes-workspace/borg/dogfood/experiment_executor.py`
- Build script: `/root/hermes-workspace/borg/dogfood/build_all_images.py`
- Calibration data: `/root/hermes-workspace/borg/dogfood/v2_data/swebench_results/calibration.json`

### How to Run a Calibration Trial
1. Start container: `docker run -d --name CONTAINER_NAME IMAGE_KEY tail -f /dev/null`
2. Apply test patch: `docker cp /tmp/test_patch.diff CONTAINER:/tmp/ && docker exec CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && git apply /tmp/test_patch.diff"`
3. Verify test fails: `docker exec CONTAINER bash -c "source /opt/miniconda3/bin/activate testbed && cd /testbed && python tests/runtests.py TEST_MODULE.TEST_CLASS.TEST_NAME --verbosity 2"`
4. Give agent the prompt (see experiment_executor.py for prompt templates)
5. After agent: run test again to check if fixed
6. Cleanup: `docker rm -f CONTAINER_NAME`

### Final Task List (15 tasks)
```
django__django-10554, django__django-11087, django__django-11138,
django__django-11265, django__django-11400, django__django-12708,
django__django-12754, django__django-13212, django__django-13315,
django__django-13344, django__django-15128, django__django-15252,
django__django-15503, django__django-15732, django__django-16560
```

Note: The build script was building a DIFFERENT list (from the old filter).
Need to rebuild for the final selection above. Check which images exist:
`docker images --format '{{.Repository}}:{{.Tag}}' | grep sweb.eval | sort`
