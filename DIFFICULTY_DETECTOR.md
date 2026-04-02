# Difficulty Detector Prototype

## Objective

Build a simple classifier that predicts whether an agent will need help based on bug description features (length, keywords, number of files mentioned, etc.).

## Background

Prior SWE-bench experiments (n=10) showed:
- Without trace (A): 40% pass rate
- With trace (B): 90% pass rate
- Improvement: +50pp (p=0.031)

This detector predicts which issues require trace assistance vs. which can be solved directly.

## Features Extracted

| Feature | Description |
|---------|-------------|
| `problem_length` | Character count of problem statement |
| `word_count` | Non-stopword token count |
| `line_count` | Newline count |
| `code_snippets` | Number of code blocks (``` and inline `) |
| `file_mentions` | Number of `.py` file references |
| `path_mentions` | Number of django/... style paths |
| `url_mentions` | Number of HTTP URLs |
| `keyword_count` | Count of difficulty-related keywords |
| `time_mentions` | Count of time estimate keywords |
| `has_traceback` | Binary: contains traceback/error |
| `has_exception` | Binary: contains exception/raise |
| `has_test_case` | Binary: contains test patterns |
| `question_marks` | Question mark count |
| `sentence_count` | Sentence count |

## Difficulty Keywords

```
regression, memory leak, race condition, deadlock, concurrent,
thread, process, async, parallel, distributed, performance,
optimization, complex, nested, inheritance, circular,
recursive, unicode, encoding, serialization, migration,
backward compatibility, deprecated, security, vulnerability,
exploit, injection, database, transaction, lock, constraint,
middleware, plugin, hook, signal, factory, singleton, decorator
```

## Rule-Based Classifier (Prototype)

```
def predict_difficulty(features, threshold=2):
    score = 0
    score += min(features["keyword_count"], 5)
    score += min(features["file_mentions"], 3)
    if features["problem_length"] > 2000: score += 1
    if features["has_test_case"] == 0: score += 1
    if features["code_snippets"] > 2: score += 1
    return score >= threshold
```

## Evaluation Results

### Dataset: 10 SWE-bench Django instances

| Metric | Value |
|--------|-------|
| Precision | 0.556 |
| Recall | 1.000 |
| F1 | 0.714 |
| Accuracy | 0.600 |
| True Positives | 5 |
| True Negatives | 1 |
| False Positives | 4 |
| False Negatives | 0 |

### Feature Analysis (Averages)

| Feature | Needed Help | No Help |
|---------|-------------|---------|
| problem_length | 457 | 500 |
| word_count | 48.2 | 55.4 |
| file_mentions | 0.4 | 1.0 |
| keyword_count | 2.0 | 2.4 |
| has_traceback | 0.2 | 0.8 |

### Per-Instance Predictions

| Instance | Predicted | Actual | Correct |
|----------|-----------|--------|---------|
| django__django-10554 | True | True | ✓ |
| django__django-11138 | True | False | ✗ |
| django__django-11265 | False | False | ✓ |
| django__django-12708 | True | False | ✗ |
| django__django-13344 | True | True | ✓ |
| django__django-15128 | True | False | ✗ |
| django__django-16560 | True | True | ✓ |
| django__django-12754 | True | False | ✗ |
| django__django-13315 | True | True | ✓ |
| django__django-15503 | True | True | ✓ |

## Observations

1. **High recall, low precision**: Classifier catches all difficult cases but over-predicts difficulty
2. **Small dataset**: Only 10 labeled instances; results are noisy
3. **Weak discriminators**: Most features show similar distributions between classes
4. **has_traceback paradox**: More traceback in easy cases (perhaps clearer error = easier fix)

## Limitations

- Only 10 training instances
- Rule-based (not ML-trained)
- Single repo (Django)
- Binary outcome only (needed help / didn't)

## Next Steps

1. **Expand dataset**: Add more SWE-bench instances across repos
2. **ML model**: Train actual classifier (logistic regression, random forest) instead of rules
3. **Cross-validation**: Proper k-fold evaluation
4. **Feature engineering**: Add more sophisticated features:
   - File path depth (deeper = harder)
   - Test count from metadata
   - Hints length from metadata
   - Error message similarity to known patterns
5. **Calibration**: Probability outputs instead of binary predictions
6. **Deployment**: Integrate into agent prompt to trigger helpful trace injection

## Code

Full implementation at: `/root/hermes-workspace/borg/dogfood/difficulty_detector.py`