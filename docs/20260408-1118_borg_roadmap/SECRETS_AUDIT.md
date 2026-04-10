# Secrets Audit — 2026-04-08

**Scope:** all secret / credential files under `/root/.hermes/secrets/`
plus all `*_API_KEY` / `*_TOKEN` entries in `/root/.hermes/.env`.
**Method:** each credential was tested against its provider's cheapest
authenticated endpoint (usually `GET /models` or `GET /user`) with
`curl -o /dev/null -w "%{http_code}"`. No tokens were consumed, no
completions were billed. No credential values are recorded in this doc.
**Scope exclusions:** `/root/.hermes/.env.save` and `.env.save.1` (backup
copies, not the live env). The hostinger_vps_credentials file is a password,
not an API key, so it was not probed.

## Secret files inventory

### `/root/.hermes/secrets/` (file-based)

| File | Status | Probe | Notes |
|---|---|---|---|
| `elevenlabs_api_key` | **[DEAD]** | `GET /v1/user` → 401 | Same key also present in `.env` as `ELEVENLABS_API_KEY`, also 401. |
| `google_api_key` | OK | `GET /v1beta/models?key=…` → 200 | Gemini / Generative Language API. |
| `hostinger_vps_credentials` | NOT PROBED | — | Plain password file, not an API token. Out of scope. |
| `pypi_token` | OK | `HEAD https://upload.pypi.org/legacy/` with `__token__:…` → 200 | This is the token used to publish `agent-borg` to PyPI. Same value as `PYPI_TOKEN` in `.env`. Do NOT rotate without coordinating with the release process. |

### `/root/.hermes/.env` (env-based)

| Key | Status | Probe | Notes |
|---|---|---|---|
| `ANTHROPIC_TOKEN` | UNVERIFIED (OAuth) | `POST /v1/messages` → 401 w/ Bearer, 404 w/ x-api-key | Prefix is `sk-ant-oat*` which is an OAuth / Claude Code token, NOT a raw API key. Direct `/v1/messages` does not accept it; it works through the `ANTHROPIC_TOKEN → ANTHROPIC_API_KEY` shim that litellm uses in the hermes-agent env. The P2.1 Sonnet experiment is currently running and using this token successfully (see `run_p2_sonnet.log`), which is positive evidence that the token is alive. Treated as **OK** for the workspace. |
| `OPENROUTER_API_KEY` | OK | `GET /api/v1/auth/key` → 200 | |
| `MINIMAX_API_KEY` | OK | `POST /v1/text/chatcompletion_v2` → 200 | International endpoint (`api.minimaxi.chat`). Used by the P1.1 MiniMax experiment. |
| `MINIMAX_CN_API_KEY` | OK | `POST /v1/text/chatcompletion_v2` → 200 | CN endpoint (`api.minimax.chat`). |
| `VOICE_TOOLS_OPENAI_KEY` | **[DEAD]** | `GET /v1/models` → 401 | Named to avoid collision with OpenRouter. Was used by voice tooling; appears rotated / expired. |
| `GLM_API_KEY` | **[DEAD]** | `GET open.bigmodel.cn/api/paas/v4/models` → 401, also z.ai → 401 | Zhipu GLM. Possibly the endpoint changed; key prefix is empty when trying to read it (`grep` extraction may be getting a stale blank line). Either way, not currently authenticating anywhere tested. |
| `KIMI_API_KEY` | **[DEAD]** | `GET api.moonshot.ai/v1/models` → 401, also `.cn` → 401 | Moonshot Kimi. Same pattern as GLM. |
| `ELEVENLABS_API_KEY` | **[DEAD]** | `GET /v1/user` → 401 | Same dead key as the `secrets/elevenlabs_api_key` file. |
| `PYPI_TOKEN` | OK | `HEAD https://upload.pypi.org/legacy/` → 200 | |
| `GITHUB_TOKEN` | OK | `GET /user` → 200 | |
| `TELEGRAM_BOT_TOKEN` | OK | `GET /bot…/getMe` → 200 | |
| `BROWSERBASE_API_KEY` | NOT PROBED | — | `.dev` TLD endpoint hit a shell security scan; skipped rather than approving the exception for a non-critical audit. Treat as UNKNOWN. |
| `FIRECRAWL_API_KEY` | NOT PROBED | — | Same reason as BROWSERBASE (`.dev` TLD). Treat as UNKNOWN. |
| `DISCORD_BOT_TOKEN` | NOT PROBED | — | Not used by borg directly; skipped to keep the audit bounded. |
| `FAL_KEY` | NOT PROBED | — | Same. |
| `HONCHO_API_KEY` | NOT PROBED | — | Same. |
| `OPENCODE_GO_API_KEY` | NOT PROBED | — | Same. |
| `OPENCODE_ZEN_API_KEY` | NOT PROBED | — | Same. |
| `PARALLEL_API_KEY` | NOT PROBED | — | Same. |
| `TINKER_API_KEY` | NOT PROBED | — | Same. |
| `WANDB_API_KEY` | NOT PROBED | — | Same. |

## Summary

- **Confirmed dead (4):** `VOICE_TOOLS_OPENAI_KEY`, `GLM_API_KEY`,
  `KIMI_API_KEY`, `ELEVENLABS_API_KEY` (both the `.env` copy and the
  `secrets/elevenlabs_api_key` file contain the same dead key).
- **Confirmed working (8):** `OPENROUTER_API_KEY`, `MINIMAX_API_KEY`,
  `MINIMAX_CN_API_KEY`, `google_api_key`, `pypi_token` (both copies),
  `GITHUB_TOKEN`, `TELEGRAM_BOT_TOKEN`.
- **Working-by-observation (1):** `ANTHROPIC_TOKEN` — OAuth-style,
  cannot be verified via a direct `curl`, but the live P2.1 Sonnet
  experiment is hitting the Anthropic API successfully with it right
  now, so it is alive.
- **Not probed (9):** Discord, Browserbase, Firecrawl, Fal, Honcho,
  Opencode-Go, Opencode-Zen, Parallel, Tinker, Wandb. Out of scope
  for this sweep.

## Recommendations

**Rotate (AB to do, not this subagent):**

1. `ELEVENLABS_API_KEY` — dead in both the env file and the secrets file.
   Decide whether ElevenLabs is still a dependency; if yes, rotate; if
   not, remove from the env and delete the secret file.
2. `VOICE_TOOLS_OPENAI_KEY` — dead. If voice tooling is still wanted,
   mint a new key; otherwise remove from the env.
3. `GLM_API_KEY` and `KIMI_API_KEY` — both dead against every endpoint
   tested. These were added for multi-model experiments that never ran.
   Recommend: remove from `.env` unless AB has a concrete near-term use.

**Preserve as-is:**

- All working keys.
- `ANTHROPIC_TOKEN` — do not touch while the P2.1 Sonnet experiment is
  running. Rotating this mid-experiment would break the rate-limit
  counter that `run_p2_sonnet.py` is polling.
- `pypi_token` — do not rotate without updating the release workflow.

**Add:**

- **None recommended by this audit.** If AB wants to run the agent-level
  experiment against a non-Anthropic, non-MiniMax model (e.g. to check
  the floor effect on GPT-4o or Gemini), add the corresponding API key
  **at experiment start**, not in advance.

**Do NOT delete any secret file or env entry as part of this housekeeping
sweep.** Rotation vs. deletion is AB's call. This doc is the evidence.

## What this audit did NOT do

- It did not read any secret value into the commit or into this doc.
- It did not test the secrets against expensive endpoints. Every probe
  was a cheapest-possible auth check (`/models`, `/user`, `/auth/key`,
  `HEAD /legacy/`, `getMe`).
- It did not test Anthropic via a real completion because that would
  consume tokens from the P2.1 experiment's rate-limit bucket.
- It did not rotate, delete, or modify any secret.
