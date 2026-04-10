# E1c Protocol — Scoring Rubric
# Borg CLI Usability Evaluation

## Overview

Scores are assigned per task and aggregated into four composite usability metrics. Each task is scored 1-5 unless otherwise noted. Higher scores indicate better usability.

---

## Task-Level Scoring

For each task, rate the following dimensions:

### T1: Task Success

| Score | Label | Definition |
|-------|-------|------------|
| 5 | Complete | Task done correctly with no help |
| 4 | Partial | Task done correctly with minimal help (1 prompt) |
| 3 | Assisted | Task done correctly with significant help (2+ prompts) |
| 2 | Incomplete | Task attempted but not completed |
| 1 | Not attempted | Task not started |

### T2: Time on Task (relative to expert time)

| Score | Label | Definition |
|-------|-------|------------|
| 5 | Expert-equivalent | Within 1.2x expert baseline |
| 4 | Near-optimal | Within 1.5x expert baseline |
| 3 | Acceptable | Within 2x expert baseline |
| 2 | Slow | 2-3x expert baseline |
| 1 | Very slow | More than 3x expert baseline |

### T3: Error Count

| Score | Label | Definition |
|-------|-------|------------|
| 5 | No errors | Zero errors or hesitations |
| 4 | Minor hesitations | 1-2 false starts / backtracks |
| 3 | Recoverable errors | Errors recovered without moderator help |
| 2 | Major errors | 3+ errors or 1 error requiring moderator intervention |
| 1 | Catastrophic failure | Cannot recover |

### T4: Cognitive Load (post-task NASA-TLX, 1-7 scale, converted to 1-5)

| Score | Label | Definition |
|-------|-------|------------|
| 5 | Very low | Mental demand score 1-2 |
| 4 | Low | Mental demand score 3 |
| 3 | Moderate | Mental demand score 4 |
| 2 | High | Mental demand score 5-6 |
| 1 | Very high | Mental demand score 7 |

---

## Composite Usability Metrics

### C1: Task Effectiveness (average of T1 across tasks)
### C2: Efficiency (average of T2 across tasks)
### C3: Error Rate (average of T3 across tasks)
### C4: Perceived Cognitive Load (average of T4 across tasks)

---

## Single Ease Question (SEQ)

After each task, ask: "How easy was this task?"  
Scale: 1 (Very Difficult) to 7 (Very Easy)

| Score | Label |
|-------|-------|
| 7 | Very Easy |
| 6 | Easy |
| 5 | Somewhat Easy |
| 4 | Neutral |
| 3 | Somewhat Difficult |
| 2 | Difficult |
| 1 | Very Difficult |

---

## System Usability Scale (SUS)

Administer the standard 10-item SUS questionnaire after all tasks.  
Scoring: Odd items: (response - 1) × 2.5; Even items: (6 - response) × 2.5.  
Sum all items for total score out of 100.

**Interpretation:**
- 90-100: Exceptional
- 80-89: Excellent
- 70-79: Good
- 60-69: OK
- 50-59: Poor
- Below 50: Unacceptable

---

## Critical Incident Log

For each observed usability issue, log:

| Field | Description |
|-------|-------------|
| Task # | Which task triggered the issue |
| Time | Timestamp |
| Severity | Critical / Major / Minor |
| Type | Confusion / Error / Navigation / Output / Other |
| Quote | Exact participant quote |
| Moderator Notes | Context and any patterns |

---

## Severity Ratings

| Level | Definition | Action |
|-------|------------|--------|
| Critical | Task cannot be completed | Must fix before release |
| Major | Task completed with significant difficulty | Should fix |
| Minor | Minor frustration, no impact on success | Consider fixing |
| Observation | Interesting finding, not a problem | Log for future study |

---

## Summary Score Sheet

**Participant ID:** ___________  **Date:** ___________  **Moderator:** ___________

| Task | Success (1-5) | Time (1-5) | Errors (1-5) | Cognitive Load (1-5) | SEQ (1-7) |
|------|--------------|------------|--------------|---------------------|----------|
| 1    |              |            |              |                     |          |
| 2    |              |            |              |                     |          |
| 3    |              |            |              |                     |          |
| 4    |              |            |              |                     |          |
| 5    |              |            |              |                     |          |
| **Avg** |          |            |              |                     |          |

**SUS Score:** _____ / 100

**Critical Incidents:** ____ count

---

## Qualitative Coding

Code open-ended feedback into these categories:
- **Positive**: Explicit praise, enjoyment, successful moments
- **Negative**: Frustration, confusion, criticism
- **Suggestion**: Proposed improvements
- **Question**: Moments of genuine curiosity about how things work
- **Error**: Specific error descriptions
- **Navigation**: Comments about finding/locating things
- **Output**: Comments about command output/results