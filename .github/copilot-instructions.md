# Copilot instructions for Borg

Borg is failure memory for AI coding agents.

## Product identity

- Canonical repo: `https://github.com/borg-farther/Borg-Directory`
- Package users install: `agent-borg`
- Commands users run: `borg`, `borg-mcp`, `borg-doctor`
- Day-one path: `pipx install agent-borg` then `borg rescue "<real error>" --short`

## Public claims boundary

Keep output honest and concrete. Borg may claim local install, CLI, stdio MCP,
security, and confidence-gating readiness only when the executable gates pass.
Do not claim public self-serve launch, 100 real users, served remote MCP, or
measured external lift until row-derived external-user evidence passes.

## Safety rules

- Do not restart, kill, signal, or reload the Hermes gateway.
- Do not edit operator `.env` or Hermes config files from this repo.
- Do not force-push, delete, archive, or clean repos without a no-loss manifest and explicit approval.
- Keep public docs pointed at `agent-borg`, `borg`, `borg-mcp`, and `borg-farther/Borg-Directory`.

## Verification

Before readiness claims, run:

```bash
python eval/run_first_user_release_gate.py
python eval/run_readiness_gates.py
python eval/real_user_rollout_gate.py  # expected nonzero until first-10 rows pass
python -m pytest -q tests/packaging/test_distribution_readiness.py tests/packaging/test_public_repo_surface.py
```
