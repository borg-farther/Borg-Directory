# BORG MCP Server Smoke Test Results

**Date:** 2026-03-28

**Server:** `/root/hermes-workspace/guild-v2/borg/integrations/mcp_server.py`

**Result:** 13/13 tools passed

---

## ✅ PASS: `borg_search`

Response preview: `{"success": true, "matches": [{"name": "agent-a-debugging", "id": "guild://converted/systematic-debugging", "problem_cla...`

---

## ✅ PASS: `borg_pull`

Response preview: `{"success": false, "error": "URI cannot be empty"}`

---

## ✅ PASS: `borg_try`

Response preview: `{"success": false, "error": "URI cannot be empty"}`

---

## ✅ PASS: `borg_observe`

Response preview: `{"success": true, "observed": true, "guidance": "\ud83e\udde0 Borg found a proven approach: **systematic-debugging** (co...`

---

## ✅ PASS: `borg_suggest`

Response preview: `{"success": true, "has_suggestion": false, "suggestions": []}`

---

## ✅ PASS: `borg_recall`

Response preview: `{"success": true, "found": false, "wrong_approaches": [], "correct_approaches": [], "total_sessions": 0}`

---

## ✅ PASS: `borg_context`

Response preview: `{"success": true, "is_git_repo": true, "recent_files": [], "uncommitted": ["README.md", "borg/core/apply.py", "borg/core...`

---

## ✅ PASS: `borg_publish`

Response preview: `{"success": true, "artifacts": [{"type": "pack", "name": "test-pack-xyz", "path": "/root/.hermes/guild/test-pack-xyz/pac...`

---

## ✅ PASS: `borg_feedback`

Response preview: `{"success": false, "error": "Session not found: test-nonexistent-session"}`

---

## ✅ PASS: `borg_init`

Response preview: `{"success": true, "pack_name": "smoke-test-pack-686891", "path": "/root/.hermes/guild/smoke-test-pack-686891/pack.yaml",...`

---

## ✅ PASS: `borg_convert`

Response preview: `{"success": false, "error": "Cannot auto-detect format for 'file.md'. Expected SKILL.md, CLAUDE.md, or a .cursorrules fi...`

---

## ✅ PASS: `borg_reputation`

Response preview: `{"success": true, "agent_id": "test-agent", "contribution_score": 0.0, "access_tier": "community", "free_rider_status": ...`

---

## ✅ PASS: `borg_apply`

Response preview: `{"success": false, "error": "Unknown action: . Use: start, checkpoint, complete"}`

---

