# Github Issues

**Confidence:** inferred
**Problem class:** Create, manage, triage, and close GitHub issues. Search existing issues, add labels, assign people, and link to PRs. Works with gh CLI or falls back to git + GitHub REST API via curl.

## Required Inputs
- task_description: what you need to accomplish

## Phases

### 1__viewing_issues
**With gh:**

```bash
gh issue list
gh issue list --state open --label "bug"
gh issue list --assignee @me
gh issue list --search "authentication error" --state all
gh issue view 42
```

**With curl:**

```bash
# List open issues
curl -s \
  -H "Authorization: auth credential $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:  # GitHub API returns PRs in /issues too
        labels = ', '.join(l['name'] for l in i['labels'])
        print(f\"#{i['number']:5}  {i['state']:6}  {labels:30}  {i['title']}\")"

# Filter by label
curl -s \
  -H "Authorization: auth credential $GITHUB_TOKEN" \
  "https://api.github.com/repos/$OWNER/$REPO/issues?state=open&labels=bug&per_page=20" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin):
    if 'pull_request' not in i:
        print(f\"#{i['number']}  {i['title']}\")"

# View a specific issue
curl -s \
  -H "Authorization: auth credential $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues/42 \
  | python3 -c "
import sys, json
i = json.load(sys.stdin)
labels = ', '.join(l['name'] for l in i['labels'])
assignees = ', '.join(a['login'] for a in i['assignees'])
print(f\"#{i['number']}: {i['title']}\")
print(f\"State: {i['state']}  Labels: {labels}  Assignees: {assignees}\")
print(f\"Author: {i['user']['login']}  Created: {i['created_at']}\")
print(f\"\n{i['body']}\")"

# Search issues
curl -s \
  -H "Authorization: auth credential $GITHUB_TOKEN" \
  "https://api.github.com/search/issues?q=authentication+error+repo:$OWNER/$REPO" \
  | python3 -c "
import sys, json
for i in json.load(sys.stdin)['items']:
    print(f\"#{i['number']}  {i['state']:6}  {i['title']}\")"
```

**Checkpoint:** Verify 1. viewing issues is complete and correct.

### 2__creating_issues
**With gh:**

```bash
gh issue create \
  --title "Login redirect ignores ?next= parameter" \
  --body "## Description
After logging in, users always land on /dashboard.

**Checkpoint:** Verify 2. creating issues is complete and correct.

### steps_to_reproduce
1. Navigate to /settings while logged out
2. Get redirected to /login?next=/settings
3. Log in
4. Actual: redirected to /dashboard (should go to /settings)

**Checkpoint:** Verify steps to reproduce is complete and correct.

### expected_behavior
Respect the ?next= query parameter." \
  --label "bug,backend" \
  --assignee "username"
```

**With curl:**

```bash
curl -s -X POST \
  -H "Authorization: auth credential $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/issues \
  -d '{
    "title": "Login redirect ignores ?next= parameter",
    "body": "## Description\nAfter logging in, users always land on /dashboard.\n\n## Steps to Reproduce\n1. Navigate to /settings while logged out\n2. Get redirected to /login?next=/settings\n3. Log in\n4. Actual: redirected to /dashboard\n\n## Expected Behavior\nRespect the ?next= query parameter.",
    "labels": ["bug", "backend"],
    "assignees": ["username"]
  }'
```

### Bug Report Template

```

**Checkpoint:** Verify expected behavior is complete and correct.

### expected_behavior
<What should happen>

**Checkpoint:** Verify expected behavior is complete and correct.

### actual_behavior
<What actually happens>

**Checkpoint:** Verify actual behavior is complete and correct.


## Examples
**Example 1:**
- Problem: User reported a bug but agent created an issue with no labels or assignee — it sat unTriaged for a week
- Solution: 2__creating_issues: Added labels (bug, backend), assignee, and linked to the relevant code file. Used the bug report template with steps to reproduce.
- Outcome: Issue picked up by backend team within 2 days. Reproducible steps included saved 30 minutes of back-and-forth.

**Example 2:**
- Problem: Agent searched for existing issues about the same bug but got 200 results — too noisy
- Solution: 1__viewing_issues: Used gh issue list --search with state filter and label filter to narrow results. Found exact duplicate in 30 seconds.
- Outcome: Linked to existing issue instead of creating duplicate. Closed new report, saved tracker noise.

**Example 3:**
- Problem: User needed to track a production incident — agent created a generic 'fix bug' issue
- Solution: 2__creating_issues: Created incident-style issue with severity:critical, steps to reproduce, actual vs expected behavior, and asked about rollback options.
- Outcome: Incident tracked properly with all stakeholders auto-notified via label routing.


## Escalation
- If stuck after 2 attempts, ask the user for guidance

---
Author: agent://hermes-seed | Confidence: inferred | Created: 2026-03-24T12:00:00Z
Evidence: Auto-generated from github-issues skill. Requires validation through usage.
Failure cases: May not apply to all github issues scenarios
