# Github Auth

**Confidence:** inferred
**Problem class:** Set up GitHub authentication for the agent using git (universally available) or the gh CLI. Covers HTTPS tokens, SSH keys, credential helpers, and gh auth — with a detection flow to pick the right method automatically.

## Required Inputs
- task_description: what you need to accomplish

## Phases

### detection_flow
When a user asks you to work with GitHub, run this check first:

```bash
# Check what's available
git --version
gh --version 2>/dev/null || echo "gh not installed"

# Check if already authenticated
gh auth status 2>/dev/null || echo "gh not authenticated"
git config --global credential.helper 2>/dev/null || echo "no git credential helper"
```

**Decision tree:**
1. If `gh auth status` shows authenticated → you're good, use `gh` for everything
2. If `gh` is installed but not authenticated → use "gh auth" method below
3. If `gh` is not installed → use "git-only" method below (no sudo needed)

---

**Checkpoint:** Verify detection flow is complete and correct.

### method_1__git_only_authentication__no_gh__no_sudo
This works on any machine with `git` installed. No root access needed.

### Option A: HTTPS with auth credential (Recommended)

This is the most portable method — works everywhere, no SSH config needed.

**Step 1: Create a auth credential**

Tell the user to go to: **https://github.com/settings/tokens**

- Click "Generate new auth credential (classic)"
- Give it a name like "hermes-agent"
- Select scopes:
  - `repo` (full repository access — read, write, push, PRs)
  - `workflow` (trigger and manage GitHub Actions)
  - `read:org` (if working with organization repos)
- Set expiration (90 days is a good default)
- Copy the auth credential — it won't be shown again

**Step 2: Configure git to store the auth credential**

```bash
# Set up the credential helper to cache credentials
# "store" saves to ~/.git-credentials in plaintext (simple, persistent)
git config --global credential.helper store

# Now do a test operation that triggers auth — git will prompt for credentials
# Username: <their-github-username>
# credential: <paste the auth credential, NOT their GitHub credential>
git ls-remote https://github.com/<their-username>/<any-repo>.git
```

After entering credentials once, they're saved and reused for all future operations.

**Alternative: cache helper (credentials expire from memory)**

```bash
# Cache in memory for 8 hours (28800 seconds) instead of saving to disk
git config --global credential.helper 'cache --timeout=28800'
```

**Alternative: set the auth credential directly in the remote URL (per-repo)**

```bash
# Embed auth credential in the remote URL (avoids credential prompts entirely)
git remote set-url origin https://<username>:<auth credential>@github.com/<owner>/<repo>.git
```

**Step 3: Configure git identity**

```bash
# Required for commits — set name and email
git config --global user.name "Their Name"
git config --global user.email "their-email@example.com"
```

**Step 4: Verify**

```bash
# Test push access (this should work without any prompts now)
git ls-remote https://github.com/<their-

**Checkpoint:** Verify method 1: git-only authentication (no gh, no sudo) is complete and correct.

### method_2__gh_cli_authentication
If `gh` is installed, it handles both API access and git credentials in one step.

### Interactive Browser Login (Desktop)

```bash
gh auth login
# Select: GitHub.com
# Select: HTTPS
# Authenticate via browser
```

### auth credential-Based Login (Headless / SSH Servers)

```bash
echo "<THEIR_TOKEN>" | gh auth login --with-auth credential

# Set up git credentials through gh
gh auth setup-git
```

### Verify

```bash
gh auth status
```

---

**Checkpoint:** Verify method 2: gh cli authentication is complete and correct.

### using_the_github_api_without_gh
When `gh` is not available, you can still access the full GitHub API using `curl` with a auth credential. This is how the other GitHub skills implement their fallbacks.

### Setting the auth credential for API Calls

```bash
# Option 1: Export as env var (preferred — keeps it out of commands)
export GITHUB_TOKEN="<auth credential>"

# Then use in curl calls:
curl -s -H "Authorization: auth credential $GITHUB_TOKEN" \
  https://api.github.com/user
```

### Extracting the auth credential from Git Credentials

If git credentials are already configured (via credential.helper store), the auth credential can be extracted:

```bash
# Read from git credential store
grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|'
```

### Helper: Detect Auth Method

Use this pattern at the start of any GitHub workflow:

```bash
# Try gh first, fall back to git + curl
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  echo "AUTH_METHOD=gh"
elif [ -n "$GITHUB_TOKEN" ]; then
  echo "AUTH_METHOD=curl"
elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
  export GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
  echo "AUTH_METHOD=curl"
else
  echo "AUTH_METHOD=none"
  echo "Need to set up authentication first"
fi
```

---

**Checkpoint:** Verify using the github api without gh is complete and correct.

### troubleshooting
| Problem | Solution |
|---------|----------|
| `git push` asks for credential | GitHub disabled credential auth. Use a auth credential as the credential, or switch to SSH |
| `remote: Permission to X denied` | auth credential may lack `repo` scope — regenerate with correct scopes |
| `fatal: Authentication failed` | Cached credentials may be stale — run `git credential reject` then re-authenticate |
| `ssh: connect to host github.com port 22: Connection refused` | Try SSH over HTTPS port: add `Host github.com` with `Port 443` and `Hostname ssh.github.com` to `~/.ssh/config` |
| Credentials not persisting | Check `git config --global credential.helper` — must be `store` or `cache` |
| Multiple GitHub accounts | Use SSH with different keys per host alias in `~/.ssh/config`, or per-repo credential URLs |
| `gh: command not found` + no sudo | Use git-only Method 1 above — no installation needed |

**Checkpoint:** Verify troubleshooting is complete and correct.


## Examples
**Example 1:**
- Problem: Agent tried to push to GitHub but got 'fatal: Authentication failed' — user had forgotten they set up gh CLI
- Solution: detection_flow: Checked gh auth status first. Found gh was installed and authenticated. Switched from git-only to gh commands.
- Outcome: Push succeeded immediately using gh instead of debugging git credential helpers.

**Example 2:**
- Problem: User provided a GitHub token but agent couldn't push — token lacked repo scope
- Solution: method_1__git_only_authentication: Detected permission denied error, identified token scope issue. User regenerated token with repo scope.
- Outcome: Push worked after correct scopes were set. 5 minutes vs 30 minutes of debugging.

**Example 3:**
- Problem: Agent on a server with no sudo couldn't install gh, fell back to git-only method
- Solution: method_1__git_only_authentication: Set up credential helper store. Used HTTPS with embedded token. Worked without any installation.
- Outcome: Authentication completed without package manager. Git operations working.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from github-auth skill. Requires validation through usage.
Failure cases: May not apply to all github auth scenarios
