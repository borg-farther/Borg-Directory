# blue team architecture

controls:
- canonical readiness snapshot in eval/gate_run_snapshot.json
- public mirrors in docs/public/status.json and docs/public/value.json
- telemetry schema contract in eval/telemetry_event_schema.json

operational policy:
- block promotion if canonical vs public parity fails
- publish proof links in docs/public/proof/index.html
