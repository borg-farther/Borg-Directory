# GitHub Cutover Closure Proof (Hard Evidence)

- Run timestamp (UTC): 2026-04-23 15:04:01
- Working repo: `/root/hermes-workspace/borg`
- Target new home: `borg-farther/Borg-Directory`
- Target old home candidate: `bensargotest-sys/agent-borg`

## Step 1 — Verify local `origin` points to new home
**Command:**
```bash
git -C /root/hermes-workspace/borg remote -v && echo '---' && git -C /root/hermes-workspace/borg remote get-url origin
```
**Exit code:** `0`
**Output:**
```text
origin	https://github.com/borg-farther/Borg-Directory.git (fetch)
origin	https://github.com/borg-farther/Borg-Directory.git (push)
---
https://github.com/borg-farther/Borg-Directory.git
```
**Result:** PASS

## Step 2 — Check `gh` auth, visibility, and metadata of both repos

### 2a) Auth status
**Command:**
```bash
cd /root/hermes-workspace/borg && gh auth status
```
**Exit code:** `0`
**Output:**
```text
github.com
  ✓ Logged in to github.com account borg-farther (/root/.config/gh/hosts.yml)
  - Active account: true
  - Git operations protocol: https
  - Token: github...PzP_***********************************************************

  ✓ Logged in to github.com account bensargotest-sys (/root/.config/gh/hosts.yml)
  - Active account: false
  - Git operations protocol: https
  - Token: ghp_************************************
  - Token scopes: 'admin:enterprise', 'admin:gpg_key', 'admin:org', 'admin:org_hook', 'admin:public_key', 'admin:repo_hook', 'admin:ssh_signing_key', 'audit_log', 'codespace', 'copilot', 'delete:packages', 'delete_repo', 'gist', 'notifications', 'project', 'repo', 'user', 'workflow', 'write:discussion', 'write:network_configurations', 'write:packages'
```

### 2b) New repo metadata
**Command:**
```bash
cd /root/hermes-workspace/borg && gh repo view borg-farther/Borg-Directory --json nameWithOwner,visibility,isPrivate,isArchived,defaultBranchRef,url,description
```
**Exit code:** `0`
**Output:**
```json
{"defaultBranchRef":{"name":"main"},"description":"","isArchived":false,"isPrivate":false,"nameWithOwner":"borg-farther/Borg-Directory","url":"https://github.com/borg-farther/Borg-Directory","visibility":"PUBLIC"}
```

### 2c) Old repo metadata
**Command:**
```bash
cd /root/hermes-workspace/borg && gh repo view bensargotest-sys/agent-borg --json nameWithOwner,visibility,isPrivate,isArchived,defaultBranchRef,url,description
```
**Exit code:** `1`
**Output / blocker:**
```text
GraphQL: Could not resolve to a Repository with the name 'bensargotest-sys/agent-borg'. (repository)
```

### 2d) Old repo REST existence check
**Command:**
```bash
cd /root/hermes-workspace/borg && gh api repos/bensargotest-sys/agent-borg
```
**Exit code:** `1`
**Output / blocker:**
```text
{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/repos#get-a-repository","status":"404"}gh: Not Found (HTTP 404)
```

**Step 2 Result:** PARTIAL (new repo verified; old repo inaccessible/not found from current auth context)

## Step 3 — If allowed and old repo exists, set old repo private
**Command attempted:**
```bash
cd /root/hermes-workspace/borg && gh api -X PATCH repos/bensargotest-sys/agent-borg -f private=true
```
**Exit code:** `1`
**Output / blocker:**
```text
{"message":"Not Found","documentation_url":"https://docs.github.com/rest/repos/repos#update-a-repository","status":"404"}gh: Not Found (HTTP 404)
```
**Result:** BLOCKED (cannot change visibility because repo unresolved/not found from this token context)

## Step 4 — Verify old repo visibility is private after change
**Command attempted:**
```bash
cd /root/hermes-workspace/borg && gh repo view bensargotest-sys/agent-borg --json visibility,isPrivate,nameWithOwner
```
**Exit code:** `1`
**Output / blocker:**
```text
GraphQL: Could not resolve to a Repository with the name 'bensargotest-sys/agent-borg'. (repository)
```
**Result:** BLOCKED (visibility cannot be attested because repo is inaccessible/not found)

## Final verdict
- Cutover local remote to new home: **VERIFIED**
- New home repo metadata/visibility via `gh`: **VERIFIED** (`PUBLIC`)
- Old home repo existence/visibility: **NOT VERIFIABLE** from current context (`404 Not Found` / GraphQL unresolved)
- Old home set-to-private operation: **FAILED due to blocker** (repo not found/inaccessible)

Overall closure status: **PARTIAL PASS** (steps 1–2(new) pass; steps 3–4 blocked by old-repo access/existence).
