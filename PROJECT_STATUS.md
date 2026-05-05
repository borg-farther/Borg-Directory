# Borg Project Status

Updated: `2026-05-04T12:08:01.491697+00:00`

## Rollout decision

- Ready for 10 users: GO
- Ready for 100 users: GO
- Ready for 1000 users: GO
- Overall: GO

## Hard gates

- version_consistency: PASS
- first_user_surface: PASS
- security_surface: PASS
- load_10: PASS
- load_100: PASS
- load_1000: PASS

## Load gates

- 10 users: passed=True total_requests=10913 p95_ms=0.6029137410223484 p99_ms=0.6239618547260761
- 100 users: passed=True total_requests=11199 p95_ms=0.5782860796898603 p99_ms=0.6126944534480573
- 1000 users: passed=True total_requests=10123 p95_ms=0.6138130091130733 p99_ms=0.6562628224492074

Canonical machine snapshot: `eval/uat_scoreboard_snapshot.json`
