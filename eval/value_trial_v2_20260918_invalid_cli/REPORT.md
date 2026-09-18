# Borg C0/C1/C2 GPT value trial

Generated: `2026-09-18T15:25:39.564509+00:00`

## Verdict

NULL — seeded Borg did not improve solve rate over empty Borg in this trial.

Primary C2-C1 risk difference: `0.0`; paired bootstrap 95% CI: `[0.0, 0.0]`; exact McNemar p: `1.0`.

## Per condition

| condition | solved / n | rate | median seconds | median tokens | Borg calls |
|---|---:|---:|---:|---:|---:|
| C0_no_borg | 0 / 8 | 0.000 | 0.9405 | None | 0 |
| C1_borg_empty | 0 / 8 | 0.000 | 0.937 | None | 0 |
| C2_borg_seeded | 0 / 8 | 0.000 | 0.942 | None | 0 |

## Claim boundary

Directional pilot only. Proven lift requires a powered preregistered replication with the C2-C1 confidence interval excluding zero.

## Paired efficiency: seeded Borg versus empty Borg

Only task pairs solved by both conditions are included; negative deltas favor seeded Borg.

| metric | pairs | median paired delta | bootstrap 95% CI | median % change | seeded lower | tie | empty lower |
|---|---:|---:|---:|---:|---:|---:|---:|
| wall_seconds | 0 | None | None | None | 0 | 0 | 0 |
| total_tokens | 0 | None | None | None | 0 | 0 | 0 |
| api_calls | 0 | None | None | None | 0 | 0 | 0 |
