#!/usr/bin/env python3
"""
Difficulty Detector Prototype

Predicts whether an agent will need help based on bug description features.
Trains on SWE-bench data with agent outcomes (A=no trace, B=with trace).
"""

import json
import re
from pathlib import Path
from typing import Any

# Feature extraction from problem statements

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "this", "that",
    "these", "those", "it", "its", "they", "them", "their", "we", "our", "you",
    "your", "i", "my", "he", "she", "him", "her", "his", "hers", "when", "where",
    "why", "how", "which", "who", "what", "not", "no", "if", "then", "else",
    "there", "here", "all", "any", "some", "each", "every", "both", "few",
    "more", "most", "other", "such", "only", "own", "same", "so", "than",
    "too", "very", "just", "also", "now", "even", "still", "well", "back",
    "only", "after", "before", "above", "below", "between", "into", "through",
    "during", "under", "again", "further", "once", "because", "about", "against",
    "out", "up", "down", "off", "over", "while", "although", "though", "if",
    "whether", "however", "therefore", "thus", "hence", "otherwise", "really",
    "actually", "basically", "simply", "exactly", "already", "always", "never",
    "sometimes", "often", "usually", "perhaps", "probably", "possibly", "certainly",
    "definitely", "surely", "certain", "particular", "specific", "especially",
    "particularly", "generally", "typically", "normally", "usually", "standard",
    "default", "normally", "recently", "currently", "previously", "originally",
    "initially", "finally", "previously", "later", "earlier", "since", "until",
}

FILE_PATTERN = re.compile(r'[\w/]+\.py|\/[\w\-./]+\.(py|js|ts|go|rs|java|cpp|c|h|md|txt)')
PATH_PATTERN = re.compile(r'(django|flask|requests|numpy|pandas|numpy|django)\/[\w/]+')
URL_PATTERN = re.compile(r'https?:\/\/[^\s]+')


def count_words(text: str) -> int:
    words = re.findall(r'\b\w+\b', text.lower())
    return len([w for w in words if w not in STOPWORDS])


def count_code_snippets(text: str) -> int:
    return len(re.findall(r'```[\s\S]*?```|`[^`]+`', text))


def count_file_mentions(text: str) -> int:
    return len(FILE_PATTERN.findall(text))


def count_path_mentions(text: str) -> int:
    return len(PATH_PATTERN.findall(text))


def count_urls(text: str) -> int:
    return len(URL_PATTERN.findall(text))


def extract_features(instance: dict) -> dict:
    """Extract features from a SWE-bench instance."""
    problem = instance.get("problem_statement", "")
    
    # Length features
    problem_length = len(problem)
    word_count = count_words(problem)
    line_count = len(problem.split('\n'))
    
    # Complexity indicators
    code_snippets = count_code_snippets(problem)
    file_mentions = count_file_mentions(problem)
    path_mentions = count_path_mentions(problem)
    url_mentions = count_urls(problem)
    
    # Keyword-based difficulty signals
    problem_lower = problem.lower()
    difficulty_keywords = [
        'regression', 'memory leak', 'race condition', 'deadlock', 'concurrent',
        'thread', 'process', 'async', 'parallel', 'distributed', 'performance',
        'optimization', 'complex', 'complicated', 'nested', 'inheritance',
        'circular', 'recursive', 'unicode', 'encoding', 'decoding', 'serialization',
        'deserialization', 'migration', 'backward', 'compatibility', 'deprecated',
        'security', 'vulnerability', 'exploit', 'injection', 'xss', 'csrf',
        'authentication', 'authorization', 'permission', 'cors', 'https', 'ssl',
        'database', 'transaction', 'lock', 'constraint', 'foreign key', 'index',
        'migration', 'schema', 'model', 'view', 'controller', 'serializer',
        'middleware', 'plugin', 'extension', 'hook', 'signal', 'observer',
        'factory', 'singleton', 'builder', 'prototype', 'adapter', 'bridge',
        'decorator', 'facade', 'proxy', 'flyweight', 'composite', 'visitor',
        'interpreter', 'iterator', 'mediator', 'memento', 'state', 'strategy',
        'template method', 'abstract factory', 'reflection', 'introspection',
    ]
    keyword_count = sum(1 for kw in difficulty_keywords if kw in problem_lower)
    
    # Time estimate signals
    time_signals = ['hour', 'minute', 'day', 'week', 'month', 'complex', 'simple', 'quick', 'easy', 'difficult']
    time_mentions = sum(1 for t in time_signals if t in problem_lower)
    
    # Error pattern indicators
    has_traceback = 'traceback' in problem_lower or 'error' in problem_lower
    has_exception = 'exception' in problem_lower or 'raise' in problem_lower
    has_test_case = 'test' in problem_lower and ('def ' in problem or 'assert' in problem)
    
    # Question marks and steps
    question_marks = problem.count('?')
    
    # Sentence count (rough complexity)
    sentences = re.split(r'[.!?]+', problem)
    sentence_count = len([s for s in sentences if s.strip()])
    
    return {
        "problem_length": problem_length,
        "word_count": word_count,
        "line_count": line_count,
        "code_snippets": code_snippets,
        "file_mentions": file_mentions,
        "path_mentions": path_mentions,
        "url_mentions": url_mentions,
        "keyword_count": keyword_count,
        "time_mentions": time_mentions,
        "has_traceback": int(has_traceback),
        "has_exception": int(has_exception),
        "has_test_case": int(has_test_case),
        "question_marks": question_marks,
        "sentence_count": sentence_count,
    }


def load_data():
    """Load SWE-bench data and results."""
    base = Path("/root/hermes-workspace/borg/dogfood/v2_data")
    
    # Load results
    with open(base / "swebench_results/FINAL_RESULTS_v2.json") as f:
        results = json.load(f)
    
    # Load task metadata
    with open(base / "swebench_results/tasks.json") as f:
        tasks = json.load(f)
    
    # Load candidates (full problem statements)
    with open(base / "swebench_django_candidates.json") as f:
        candidates = json.load(f)
    
    return results, tasks, candidates


def build_dataset():
    """Build labeled dataset from results and features."""
    results, tasks, candidates = load_data()
    
    # Index candidates by instance_id
    candidate_map = {c["instance_id"]: c for c in candidates}
    
    # Build dataset
    X = []  # features
    y = []  # labels (True=needed help/B, False=passed without help/A)
    instance_ids = []
    
    for instance_id, result in results["results"].items():
        if instance_id not in candidate_map:
            continue
        
        # Label: True if agent failed without trace (A=False) but succeeded with trace (B=True)
        # i.e., "needed help" = A failed but B passed
        needed_help = (result["A"] == False) and (result["B"] == True)
        
        features = extract_features(candidate_map[instance_id])
        X.append(features)
        y.append(needed_help)
        instance_ids.append(instance_id)
    
    return X, y, instance_ids


def train_simple_classifier(X, y):
    """Train a simple rule-based classifier (prototype)."""
    # For this prototype, use keyword-based rules
    # Future: replace with actual ML model
    
    # Extract key features
    features_used = []
    for xi in X:
        features_used.append({
            "keyword_count": xi["keyword_count"],
            "file_mentions": xi["file_mentions"],
            "problem_length": xi["problem_length"],
            "has_test_case": xi["has_test_case"],
            "code_snippets": xi["code_snippets"],
        })
    
    return features_used, y


def predict_difficulty(features, threshold=2):
    """
    Simple rule-based difficulty prediction.
    Returns True if agent will likely need help.
    """
    score = 0
    score += min(features["keyword_count"], 5)  # cap at 5
    score += min(features["file_mentions"], 3)  # cap at 3
    if features["problem_length"] > 2000:
        score += 1
    if features["has_test_case"] == 0:
        score += 1
    if features["code_snippets"] > 2:
        score += 1
    
    return score >= threshold


def evaluate():
    """Evaluate the difficulty detector on our data."""
    X, y, instance_ids = build_dataset()
    
    print(f"Dataset: {len(X)} instances")
    print(f"Positive (needed help): {sum(y)} ({100*sum(y)/len(y):.1f}%)")
    print(f"Negative (did not need help): {len(y) - sum(y)}")
    print()
    
    # Predict
    predictions = [predict_difficulty(xi) for xi in X]
    
    # Metrics
    tp = sum(1 for i in range(len(y)) if y[i] and predictions[i])
    tn = sum(1 for i in range(len(y)) if not y[i] and not predictions[i])
    fp = sum(1 for i in range(len(y)) if not y[i] and predictions[i])
    fn = sum(1 for i in range(len(y)) if y[i] and not predictions[i])
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn)
    
    print("=== Simple Rule-Based Classifier ===")
    print(f"Precision: {precision:.3f}")
    print(f"Recall: {recall:.3f}")
    print(f"F1: {f1:.3f}")
    print(f"Accuracy: {accuracy:.3f}")
    print()
    print(f"TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
    print()
    
    # Feature analysis
    print("=== Feature Analysis ===")
    feature_names = list(X[0].keys())
    for fname in feature_names:
        vals_needed_help = [xi[fname] for i, xi in enumerate(X) if y[i]]
        vals_no_help = [xi[fname] for i, xi in enumerate(X) if not y[i]]
        if vals_needed_help and vals_no_help:
            avg_needed = sum(vals_needed_help) / len(vals_needed_help)
            avg_no_help = sum(vals_no_help) / len(vals_no_help)
            print(f"{fname}: needed_help_avg={avg_needed:.2f}, no_help_avg={avg_no_help:.2f}")
    
    # Show predictions for each instance
    print()
    print("=== Per-Instance Predictions ===")
    for i, (xi, pred, label) in enumerate(zip(X, predictions, y)):
        status = "✓" if pred == label else "✗"
        print(f"{instance_ids[i]}: pred={pred}, actual={label} {status}")
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
    }


if __name__ == "__main__":
    evaluate()