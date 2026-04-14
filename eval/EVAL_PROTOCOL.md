# BORG Evaluation Protocol v1.0

> No Borg change ships to production unless it improves real task performance under controlled conditions.

## Decision Framework
- **SHIP**: Clear practical improvement, acceptable risk, no severe regressions
- **HOLD**: Ambiguous signal, needs more data
- **KILL**: No benefit or causes regressions

## Gates
1. **Offline Benchmark**  50 tasks (A:helpful/B:neutral/C:risky), control vs treatment
2. **Shadow Mode**  Run on live tasks silently, log but don't inject
3. **Live A/B**  Randomised, pre-defined success threshold, stratified
4. **Progressive Rollout**  1%5%20%50%100% with rollback triggers

## Primary Metric
Successful task completion rate (binary: did the task get done?)

## Ship Criteria
- Completion rate lifts >=5% relative
- Tokens/success not worse >10%
- No severe failure rate increase
- No Bucket C regression
- Replicates across 2 windows

## Selective Activation Rule
Activate Borg for tasks with complexity>=medium AND trace_relevance>=0.7.

## First Experiment: BORG-000
- Arms: Borg ON vs OFF
- 50 tasks, 3 buckets
- Result: HOLD (Bucket A +65%, Bucket C -40%). Fix: confidence gate at 0.7.

See benchmark_runner.py and instrumentation_schema.py for execution tools.
