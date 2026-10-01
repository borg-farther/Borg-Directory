# Borg C0/C1/C2 GPT value trial

Generated: `2026-09-18T15:11:22.184777+00:00`

## Verdict

NULL — seeded Borg did not improve solve rate over empty Borg in this trial.

Primary C2-C1 risk difference: `0.0`; paired bootstrap 95% CI: `[0.0, 0.0]`; exact McNemar p: `1.0`.

## Per condition

| condition | solved / n | rate | median seconds | median tokens | Borg calls |
|---|---:|---:|---:|---:|---:|
| C0_no_borg | 8 / 8 | 1.000 | 70.333 | 70658.0 | 0 |
| C1_borg_empty | 8 / 8 | 1.000 | 61.837500000000006 | 83797.0 | 8 |
| C2_borg_seeded | 8 / 8 | 1.000 | 54.677 | 76505.5 | 8 |

## Claim boundary

This pilot has a solve-rate ceiling: every arm solved every task, so it provides no evidence of solve-rate lift. Efficiency findings are directional secondary metrics only. Proven value requires a harder powered preregistered replication whose primary C2-C1 confidence interval excludes zero.

## Paired efficiency: seeded Borg versus empty Borg

Only task pairs solved by both conditions are included; negative deltas favor seeded Borg.

| metric | pairs | median paired delta | bootstrap 95% CI | median % change | seeded lower | tie | empty lower |
|---|---:|---:|---:|---:|---:|---:|---:|
| wall_seconds | 8 | -6.297999999999995 | [-10.212999999999994, 10.555999999999994] | -10.239691996247824 | 6 | 0 | 2 |
| total_tokens | 8 | -8332.5 | [-19077.0, 9421.0] | -9.040800203457822 | 4 | 0 | 4 |
| api_calls | 8 | -0.5 | [-2.0, 0.5] | -5.0 | 4 | 2 | 2 |
