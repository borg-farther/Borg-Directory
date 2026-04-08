# Borg Authorship Standard

**Effective:** 2026-04-08 (workspace housekeeping sweep)
**Enforced by:** `.git/hooks/pre-commit` (installed, tested, bypassable)
**Scope:** all commits to the `borg` repository

## The rule

Every commit to `borg` must be authored as:

    user.name  = Hermes Agent
    user.email = aleshbrown@gmail.com

This is AB's canonical identity for this repository. The pre-commit hook
reads `git var GIT_AUTHOR_IDENT` (which captures per-commit `git -c` overrides
as well as the repo-level config) and refuses any commit that does not match
both fields.

## Why

Subagent prompts have historically overridden `user.name` to things like
"Claude Code" (the vendor brand for this model). That is not AB's identity
and it pollutes `git log --author`, making it hard to audit who actually
produced a commit in this workspace vs. in other repos where the same agent
operates under a different convention.

The correction was to **document the canonical identity and enforce it at
commit time**, not to rewrite history. Existing commits with the wrong
author name are preserved as-is — git history is a forensic record, not a
canvas.

## Three ways to comply

**Preferred — set it once on this repo:**

```bash
cd /root/hermes-workspace/borg
git config user.name  'Hermes Agent'
git config user.email 'aleshbrown@gmail.com'
```

**For subagents — override per commit:**

```bash
git -c user.name='Hermes Agent' -c user.email='aleshbrown@gmail.com' commit -m "..."
```

This is what the housekeeping commit that installed this standard uses,
because a subagent cannot rely on the repo-level config surviving whatever
wrapper invoked it.

**Emergency bypass:**

```bash
git commit --no-verify -m "..."
```

Only use `--no-verify` when you genuinely cannot set the author (e.g.
`git rebase --exec` with a fixed author on an imported branch). Log the
reason in the commit message.

## What the hook does NOT do

- It does not amend or rewrite existing commits. History is preserved.
- It does not check the committer field, only the author field.
- It does not run on `git cherry-pick -n`, `git stash`, or any operation
  that does not produce a commit object.
- It does not network, lint, or block on test state. It is the single
  cheapest possible check.

## Why a pre-commit hook and not commit-msg

A `commit-msg` hook runs after git has already built the commit object and
written it to the object store; at that point the author is baked in and
the hook can only reject via exit code. A `pre-commit` hook runs before
the commit object is created, which means:

1. It can read `git var GIT_AUTHOR_IDENT`, which reflects any `git -c`
   overrides the caller passed.
2. Rejecting it leaves the index clean and the working tree untouched.
3. The error message can direct the user to the fix before any commit
   object exists at all.

## Testing the hook

```bash
# Should be rejected
git -c user.name='Claude Code' commit --allow-empty -m test

# Should pass
git -c user.name='Hermes Agent' -c user.email='aleshbrown@gmail.com' \
    commit --allow-empty -m test

# Should bypass
git -c user.name='Claude Code' commit --no-verify --allow-empty -m test
```

The install of this hook on 2026-04-08 was verified against all three
scenarios in an isolated `/tmp` repo before being dropped into
`.git/hooks/pre-commit`.

## Not in scope

- Enforcing this standard in **other** hermes-workspace repos. Each repo
  has its own identity convention (e.g. `hermes-agent` uses a different
  email). Copy this hook if you want the same enforcement elsewhere,
  editing the `expected_name` / `expected_email` variables.
- Retroactive cleanup of existing wrongly-authored commits. Explicitly
  rejected: rewriting history loses forensic signal.
