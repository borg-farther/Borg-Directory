# E1c Protocol — Human Evaluation Protocol for CLI Usability
# Borg CLI Evaluation

## Overview

The E1c protocol defines a complete human evaluation methodology for assessing the usability of Borg's command-line interface. It combines established UX research methods (think-aloud, SUS, NASA-TLX) with CLI-specific adaptations.

## Protocol Components

| File | Purpose |
|------|---------|
| `screening_form.md` | Pre-screening questionnaire to recruit qualified participants |
| `consent_form.md` | Informed consent documentation (IRB-compliant) |
| `think_aloud_guide.md` | Moderator script and techniques for verbal protocol capture |
| `scoring_rubric.md` | Quantitative scoring dimensions and severity ratings |
| `test_harness.py` | Python CLI tool for session management and data analysis |
| `tasks.json` | Definition of 5 standardized evaluation tasks |
| `README.md` | This file |

## Quick Start

### 1. Recruit Participants
Use `screening_form.md` to verify eligibility. Required criteria:
- ≥1 year CLI experience
- Weekly or daily CLI usage
- Familiarity with ≥2 CLI tools
- Comfortable learning new tools

### 2. Obtain Consent
Have participants sign `consent_form.md` before the session.

### 3. Run Evaluation Session

```bash
# Test the harness (simulated mode)
python test_harness.py --mode=session --participant-id=test-001

# Run analysis on collected data
python test_harness.py --mode=analysis

# Generate summary report
python test_harness.py --mode=report
```

### 4. Scoring

Each task is scored 1-5 on four dimensions:
- **Task Success**: Can the participant complete the task?
- **Time**: How long relative to expert baseline?
- **Errors**: How many errors or backtracks?
- **Cognitive Load**: Post-task NASA-TLX assessment

After all tasks, administer the standard 10-item SUS questionnaire.

### 5. Interpret Results

| SUS Score | Interpretation |
|-----------|----------------|
| 90-100 | Exceptional |
| 80-89 | Excellent |
| 70-79 | Good |
| 60-69 | OK |
| 50-59 | Poor |
| <50 | Unacceptable |

## Tasks

The protocol includes 5 standardized tasks:

1. **Initial Setup** — Install and configure Borg CLI
2. **Search for a Pattern** — Find approaches via search
3. **Apply an Approach** — Use an existing approach
4. **Custom Query** — Ask Borg for advice
5. **Feedback Loop** — Submit feedback on an approach

Each task has defined success criteria, expert time baselines, and acceptable hints.

## Critical Incidents

Log any significant usability issues observed during the session:
- Timestamp
- Task that triggered the issue
- Severity (Critical / Major / Minor / Observation)
- Exact participant quote (verbatim)
- Moderator observations

## Data Storage

Session data is stored in `data/sessions/` as JSON files. Each session includes:
- Participant metadata
- Per-task results (scores, incidents, timing)
- SUS responses
- Post-task questionnaire responses
- Moderator notes

## Moderator Checklist

- [ ] Verify screening eligibility
- [ ] Obtain signed consent
- [ ] Start screen recording
- [ ] Conduct session using think-aloud protocol
- [ ] Administer SEQ after each task
- [ ] Administer NASA-TLX after each task
- [ ] Administer SUS after all tasks
- [ ] Conduct post-task interview
- [ ] Save and backup session data
- [ ] Thank participant

## Ethical Considerations

- All participants must provide informed consent
- Data must be anonymized before analysis
- Participants may withdraw at any time
- Raw recordings must be stored securely
- Compensation must be provided as promised

## References

- Nielsen, J. (1994). "Think-Aloud Protocols." In _Usability Inspection Methods_.
- Brooke, J. (1996). "SUS: A Quick and Dirty Usability Scale." _Usability Evaluation in Industry_.
- Hart, S. G., & Staveland, L. E. (1988). "Development of NASA-TLX." _Work & Stress_.

## Version

E1c Protocol v1.0 — Borg CLI Usability Evaluation