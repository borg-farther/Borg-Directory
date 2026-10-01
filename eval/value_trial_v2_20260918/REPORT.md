# Borg C0/C1/C2 GPT value trial

Generated: `2026-09-18T15:49:20.600706+00:00`

## Verdict

NULL — seeded Borg did not improve solve rate over empty Borg in this trial.

Primary C2-C1 risk difference: `0.0`; paired bootstrap 95% CI: `[0.0, 0.0]`; exact McNemar p: `1.0`.

## Per condition

| condition | solved / n | rate | median seconds | median tokens | Borg calls |
|---|---:|---:|---:|---:|---:|
| C0_no_borg | 8 / 8 | 1.000 | 62.355999999999995 | 67412.5 | 0 |
| C1_borg_empty | 8 / 8 | 1.000 | 69.7295 | 87987.0 | 8 |
| C2_borg_seeded | 8 / 8 | 1.000 | 73.82849999999999 | 87115.0 | 8 |

## Claim boundary

This pilot has a solve-rate ceiling: every arm solved every task, so it provides no evidence of solve-rate lift. Efficiency findings are directional secondary metrics only. Proven value requires a harder powered preregistered replication whose primary C2-C1 confidence interval excludes zero.

## Paired efficiency: seeded Borg versus empty Borg

Only task pairs solved by both conditions are included; negative deltas favor seeded Borg.

| metric | pairs | median paired delta | bootstrap 95% CI | median % change | seeded lower | tie | empty lower |
|---|---:|---:|---:|---:|---:|---:|---:|
| wall_seconds | 8 | 8.959500000000002 | [-12.097999999999999, 51.341] | 12.782541958656667 | 3 | 0 | 5 |
| total_tokens | 8 | 10892.5 | [-26892.0, 31701.0] | 12.649628541182116 | 3 | 0 | 5 |
| api_calls | 8 | 1.0 | [-3.0, 3.0] | 11.11111111111111 | 2 | 2 | 4 |
