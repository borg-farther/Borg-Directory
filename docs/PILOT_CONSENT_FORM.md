# Pilot Consent Form — Rescue-Receipt Replay

**One page, plain English. Sign before day 0 of the pilot. You can withdraw at
any time without giving a reason.**

## What this is about

During the 14-day pilot, Borg keeps a small local log ("rescue receipts") of
each time it fired: what *class* of error it was, whether Borg matched a known
fix, and a **redacted** copy of the error text. At the end of the pilot we ask
you to share those receipts so we can measure — honestly — whether Borg's help
was real.

## What is collected

- **Redacted rescue receipts only.** Each one contains: the error text *after*
  secret/PII redaction, an environment fingerprint (OS / Python version / Borg
  version — nothing else), the class of problem, the fix Borg surfaced, and
  whether it worked.
- You export them **yourself** with `borg receipts export --out <file>`. The
  command shows you the **complete content** before writing anything, and
  writes nothing without your confirmation. What you see is byte-for-byte what
  we receive.

## What it is used for

- **One thing:** an offline "counterfactual replay" run by the pilot operator —
  each receipt is replayed against a pinned AI model *without* Borg's knowledge
  to ask: *would the agent have gotten unstuck anyway?* The aggregate rate
  decides whether Borg is worth building further
  (`docs/PILOT_DECISION_PROTOCOL.md`). Nothing is used for training, marketing,
  or anything not listed here.

## What never leaves your machine

- Raw error text (pre-redaction), your code, file contents, file paths,
  secrets, API keys, environment variables, prompts, conversation history,
  anything identifying your employer or project. Receipts are redacted **at
  write time** — the raw text is never stored, so it cannot be exported.
- During the pilot itself, **nothing** leaves your machine at all: sharing is
  off and fail-closed; the export at day 14 is a file you hand over manually,
  or don't.

## Your rights

- **See everything:** `borg receipts list` any time.
- **Delete anything:** `borg receipts delete --id N` or `--all` — permanent,
  local, no questions. Deleted receipts can't be exported.
- **Withdraw:** tell the operator at any point, before or after export; your
  exported receipts and any replay results derived from them are destroyed and
  excluded from the decision.
- **Reproducibility:** the replay report that includes your receipts is
  archived with your consent attestation; you may request a copy.

## Duration

- Pilot: 14 days from your day 0. Export request: day 14. Your exported
  receipts are kept only until the pilot decision is written (day 15 target)
  plus 30 days for audit, then deleted.

## Agreement

I understand what is collected (redacted rescue receipts only), what it is
used for (offline counterfactual replay), what never leaves my machine, and my
deletion/withdrawal rights.

| | |
|---|---|
| Name | _______________________ |
| Date | _______________________ |
| Signature | _______________________ |
| Operator countersign | _______________________ |
