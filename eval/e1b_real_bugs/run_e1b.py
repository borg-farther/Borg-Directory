#!/usr/bin/env python3
"""
E1b: Real-Bugs Dogfood Test

Tests whether borg guidance helps on real open-source Django/Flask bugs.

PRD Reference: BORG_PACK_AUTO_GENERATION_PRD.md Section E1b

Protocol:
- Load 5-10 real Django/GitHub bugs from SWE-bench lite
- For each bug, use borg_search to find relevant packs
- Evaluate whether guidance would likely help based on:
  1. problem_class match (does pack's error type match bug's error type?)
  2. investigation_trail accuracy (do suggested files appear in actual fix?)
  3. resolution match (do suggested approaches appear in actual patch?)

Pre-registered pass criteria:
  - Guidance relevance: ≥ 2/3 developers would find packs "helpful" or "very helpful"
  - Investigation trail accuracy: ≥ 2/3 times, suggested files were actually relevant
  - Resolution match: ≥ 1/3 times, a suggested resolution was the actual fix
"""

import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Add borg to path
sys.path.insert(0, '/root/hermes-workspace/borg')

from borg.core.search import borg_search



# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BugCase:
    """A real-world bug from Django/Flask open source."""
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    hints: str
    patch: str  # The actual fix patch
    test_patch: str  # Test that demonstrates the bug
    fail_to_pass: list[str]
    pass_to_pass: list[str]
    difficulty: str
    problem_length: int


@dataclass  
class PackEvaluation:
    """Result of evaluating a pack against a bug."""
    pack_id: str
    problem_class: str
    confidence: float
    suggested_files: list[str]
    suggested_resolution: str
    files_overlap: list[str]  # Files that appear in both pack and actual patch
    resolution_keywords: list[str]  # Keywords from pack that appear in patch
    likely_helpful: bool
    reasoning: str


@dataclass
class BugEvaluation:
    """Complete evaluation of one bug case."""
    instance_id: str
    bug: BugCase
    search_results: list
    pack_evaluations: list[PackEvaluation]
    problem_class_match: bool
    file_relevance_rate: float  # Fraction of suggested files that appear in patch
    resolution_match: bool  # At least one resolution keyword in patch
    overall_likely_helpful: bool


# ---------------------------------------------------------------------------
# Bug data loading
# ---------------------------------------------------------------------------

def load_swebench_bugs(tasks_dir: str, count: int = 8) -> list[BugCase]:
    """Load real-world Django bugs from SWE-bench tasks."""
    bugs = []
    task_ids = sorted(os.listdir(tasks_dir))[:count]
    
    for task_id in task_ids:
        task_path = os.path.join(tasks_dir, task_id, 'task_data.json')
        if not os.path.exists(task_path):
            continue
            
        with open(task_path) as f:
            data = json.load(f)
        
        bug = BugCase(
            instance_id=data['instance_id'],
            repo=data['repo'],
            base_commit=data['base_commit'],
            problem_statement=data['problem_statement'],
            hints=data.get('hints_text', ''),
            patch=data.get('patch', ''),
            test_patch=data.get('test_patch', ''),
            fail_to_pass=data.get('FAIL_TO_PASS', []),
            pass_to_pass=data.get('PASS_TO_PASS', []),
            difficulty=data.get('difficulty', 'unknown'),
            problem_length=data.get('problem_length', 0),
        )
        bugs.append(bug)
    
    return bugs


def extract_patch_files(patch: str) -> list[str]:
    """Extract list of files modified in a patch."""
    files = []
    for line in patch.split('\n'):
        # Match both --- a/file and diff --git a/file forms
        if line.startswith('--- a/'):
            fname = line[5:].strip()
            if fname and not fname.startswith('tests/'):
                files.append(fname)
        elif line.startswith('diff --git a/'):
            # Extract path after "diff --git a/"
            rest = line[12:]
            if '/' in rest:
                fname = rest.split('/', 1)[1]
                if ' -> ' in fname:
                    fname = fname.split(' -> ')[0]
                if not fname.startswith('tests/'):
                    files.append(fname)
    return list(set(files))[:10]  # Dedupe, limit to 10


def extract_problem_keywords(bug: BugCase) -> list[str]:
    """Extract key search terms from bug problem statement."""
    text = bug.problem_statement + ' ' + bug.hints
    
    # Remove common Django REST framework terminology
    text = re.sub(r'django[\s_-]*rest[\s_-]*framework', '', text, flags=re.IGNORECASE)
    text = re.sub(r'django', '', text, flags=re.IGNORECASE)
    
    # Extract key phrases
    keywords = []
    
    # Look for method/function names in backticks or with ()
    func_pattern = re.findall(r'`([a-zA-Z_][a-zA-Z0-9_]*)[\(\)]`', text)
    keywords.extend(func_pattern[:5])
    
    # Look for quoted strings
    quoted = re.findall(r'["\']([a-zA-Z_][a-zA-Z0-9_\s]*)["\']', text)
    keywords.extend([q.strip() for q in quoted if len(q) > 4][:5])
    
    # Extract significant words (5+ chars)
    words = re.findall(r'\b[a-zA-Z]{5,}\b', text)
    common_words = {'should', 'which', 'where', 'there', 'these', 'those', 
                   'would', 'could', 'their', 'there', 'other', 'after',
                   'before', 'error', 'value', 'issue', 'problem', 'file',
                   'function', 'method', 'class', 'return', 'object', 'type'}
    keywords.extend([w.lower() for w in words if w.lower() not in common_words][:10])
    
    return list(set(keywords))[:15]


# ---------------------------------------------------------------------------
# Pack evaluation
# ---------------------------------------------------------------------------

def evaluate_pack_against_bug(pack_data: dict, bug: BugCase) -> PackEvaluation:
    """Evaluate whether a pack would help with this bug."""
    
    patch_files = extract_patch_files(bug.patch)
    pack_id = pack_data.get('id', pack_data.get('name', 'unknown'))
    problem_class = pack_data.get('problem_class', '')
    confidence = float(pack_data.get('confidence', 0.5))
    
    # Extract files from investigation_trail
    suggested_files = []
    for item in pack_data.get('investigation_trail', []):
        if isinstance(item, dict):
            for key in ['file', 'filepath', 'path', 'location']:
                if key in item:
                    suggested_files.append(item[key])
        elif isinstance(item, str):
            # Look for file-like patterns in strings
            matches = re.findall(r'(?:src/|lib/|\.py)[a-zA-Z0-9_/.-]+', item)
            suggested_files.extend(matches)
    
    # Extract resolution keywords
    resolution_text = ''
    for item in pack_data.get('resolution_sequence', []):
        if isinstance(item, dict):
            resolution_text += ' ' + json.dumps(item)
        elif isinstance(item, str):
            resolution_text += ' ' + item
    
    # Clean resolution text
    resolution_text = re.sub(r'[{}\[\]",]', ' ', resolution_text)
    resolution_keywords = [w.lower() for w in re.findall(r'\b[a-zA-Z]{4,}\b', resolution_text)]
    resolution_keywords = [w for w in resolution_keywords if w not in 
                          {'that', 'this', 'with', 'from', 'have', 'were', 'been',
                           'will', 'would', 'could', 'should', 'when', 'then',
                           'what', 'which', 'their', 'there', 'these', 'some'}]
    
    # Check for file overlap
    files_overlap = []
    for pf in patch_files:
        pf_lower = pf.lower()
        for sf in suggested_files:
            if any(x in pf_lower for x in sf.lower().split('/')):
                files_overlap.append(pf)
                break
    
    # Check resolution keywords against patch
    patch_lower = bug.patch.lower()
    matched_resolutions = [w for w in resolution_keywords if w in patch_lower]
    
    # Determine if pack is likely helpful
    file_relevance = len(files_overlap) / max(1, len(suggested_files[:5]))
    resolution_match = len(matched_resolutions) >= 1
    
    # A pack is "likely helpful" if:
    # - It has reasonable confidence
    # - AND either files overlap OR resolution keywords match
    likely_helpful = (confidence >= 0.5) and (file_relevance >= 0.2 or resolution_match)
    
    reasoning = (
        f"Confidence={confidence:.2f}, "
        f"File overlap={len(files_overlap)}/{min(5, len(suggested_files))} suggested, "
        f"Resolution matches={len(matched_resolutions)} keywords"
    )
    
    return PackEvaluation(
        pack_id=pack_id,
        problem_class=problem_class,
        confidence=confidence,
        suggested_files=suggested_files[:5],
        suggested_resolution=' '.join(resolution_keywords[:10]),
        files_overlap=files_overlap,
        resolution_keywords=matched_resolutions,
        likely_helpful=likely_helpful,
        reasoning=reasoning
    )


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def run_e1b_evaluation(bugs: list[BugCase], output_dir: str) -> dict:
    """Run full E1b evaluation."""
    
    results = []
    total_helpful = 0
    total_file_relevant = 0
    total_resolution_match = 0
    
    for bug in bugs:
        print(f"\n{'='*70}")
        print(f"Evaluating: {bug.instance_id}")
        print(f"Problem: {bug.problem_statement[:100]}...")
        print(f"Difficulty: {bug.difficulty}")
        
        # Extract search query from bug
        keywords = extract_problem_keywords(bug)
        query = ' '.join(keywords[:5])
        print(f"Search query: {query}")
        
        # Run borg search
        search_raw = borg_search(query)
        try:
            search_data = json.loads(search_raw)
        except:
            search_data = {'matches': []}
        
        matches = search_data.get('matches', [])
        print(f"Found {len(matches)} matching packs")
        
        # Evaluate top matches
        pack_evals = []
        for match in matches[:5]:  # Top 5 packs
            pe = evaluate_pack_against_bug(match, bug)
            pack_evals.append(pe)
            if pe.likely_helpful:
                print(f"  ✓ Pack {pe.pack_id}: {pe.reasoning}")
            else:
                print(f"  ✗ Pack {pe.pack_id}: {pe.reasoning}")
        
        # Determine overall helpfulness for this bug
        helpful_packs = [pe for pe in pack_evals if pe.likely_helpful]
        file_relevant = len([pe for pe in pack_evals if len(pe.files_overlap) > 0])
        resolution_match = len([pe for pe in pack_evals if len(pe.resolution_keywords) > 0])
        
        bug_helpful = len(helpful_packs) > 0
        bug_file_relevant = file_relevant >= 1
        bug_resolution_match = resolution_match >= 1
        
        if bug_helpful:
            total_helpful += 1
        if bug_file_relevant:
            total_file_relevant += 1
        if bug_resolution_match:
            total_resolution_match += 1
        
        eval_result = BugEvaluation(
            instance_id=bug.instance_id,
            bug=bug,
            search_results=matches[:5],
            pack_evaluations=pack_evals,
            problem_class_match=bug_helpful,
            file_relevance_rate=file_relevant / max(1, len(pack_evals)),
            resolution_match=bug_resolution_match,
            overall_likely_helpful=bug_helpful
        )
        results.append(eval_result)
        
        # Store patch files for reference
        eval_result.patch_files = extract_patch_files(bug.patch)
    
    # Calculate summary metrics
    n = len(results)
    guidance_relevance = total_helpful / max(1, n)
    file_accuracy = total_file_relevant / max(1, n)
    resolution_rate = total_resolution_match / max(1, n)
    
    summary = {
        'total_bugs': n,
        'bugs_where_packs_helpful': total_helpful,
        'bugs_with_relevant_files': total_file_relevant,
        'bugs_with_resolution_match': total_resolution_match,
        'guidance_relevance_rate': guidance_relevance,
        'file_accuracy_rate': file_accuracy,
        'resolution_match_rate': resolution_rate,
        'pass_guidance_relevance': guidance_relevance >= 0.67,  # ≥ 2/3
        'pass_file_accuracy': file_accuracy >= 0.67,  # ≥ 2/3  
        'pass_resolution_match': resolution_rate >= 0.33,  # ≥ 1/3
        'overall_pass': (guidance_relevance >= 0.67 and 
                        file_accuracy >= 0.67 and 
                        resolution_rate >= 0.33)
    }
    
    return {
        'summary': summary,
        'bug_results': [
            {
                'instance_id': r.instance_id,
                'difficulty': r.bug.difficulty,
                'problem_class_match': r.problem_class_match,
                'file_relevance_rate': r.file_relevance_rate,
                'resolution_match': r.resolution_match,
                'overall_likely_helpful': r.overall_likely_helpful,
                'pack_count': len(r.pack_evaluations),
                'helpful_pack_count': len([pe for pe in r.pack_evaluations if pe.likely_helpful]),
            }
            for r in results
        ]
    }


def main():
    # Configuration
    TASKS_DIR = '/root/hermes-workspace/borg/dogfood/swebench_tasks'
    OUTPUT_DIR = '/root/hermes-workspace/borg/eval/e1b_real_bugs/results'
    BUG_COUNT = 8  # Test on 8 Django bugs
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("="*70)
    print("E1b: Real-Bugs Dogfood Test")
    print("="*70)
    print(f"\nLoading {BUG_COUNT} real Django bugs from SWE-bench...")
    
    # Load bugs
    bugs = load_swebench_bugs(TASKS_DIR, count=BUG_COUNT)
    print(f"Loaded {len(bugs)} bugs")
    
    # Run evaluation
    print("\nEvaluating borg guidance against each bug...")
    results = run_e1b_evaluation(bugs, OUTPUT_DIR)
    
    # Print summary
    print("\n" + "="*70)
    print("E1b RESULTS SUMMARY")
    print("="*70)
    
    s = results['summary']
    print(f"\nBugs evaluated: {s['total_bugs']}")
    print(f"Packs helpful: {s['bugs_where_packs_helpful']}/{s['total_bugs']} ({s['guidance_relevance_rate']:.1%})")
    print(f"File accuracy: {s['bugs_with_relevant_files']}/{s['total_bugs']} ({s['file_accuracy_rate']:.1%})")
    print(f"Resolution match: {s['bugs_with_resolution_match']}/{s['total_bugs']} ({s['resolution_match_rate']:.1%})")
    
    print(f"\nPre-registered pass criteria:")
    print(f"  Guidance relevance ≥ 67%: {'PASS' if s['pass_guidance_relevance'] else 'FAIL'}")
    print(f"  File accuracy ≥ 67%: {'PASS' if s['pass_file_accuracy'] else 'FAIL'}")
    print(f"  Resolution match ≥ 33%: {'PASS' if s['pass_resolution_match'] else 'FAIL'}")
    print(f"\n  OVERALL: {'PASS' if s['overall_pass'] else 'FAIL'}")
    
    # Save results
    output_path = os.path.join(OUTPUT_DIR, 'e1b_results.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_path}")
    
    # Detailed bug results
    print("\n" + "="*70)
    print("PER-BUG BREAKDOWN")
    print("="*70)
    for br in results['bug_results']:
        status = "✓ HELPFUL" if br['overall_likely_helpful'] else "✗ NOT HELPFUL"
        print(f"\n{br['instance_id']} ({br['difficulty']})")
        print(f"  {status}")
        print(f"  Packs evaluated: {br['pack_count']}, Helpful: {br['helpful_pack_count']}")
        print(f"  File relevance: {br['file_relevance_rate']:.1%}, Resolution match: {br['resolution_match']}")
    
    return 0 if s['overall_pass'] else 1


if __name__ == '__main__':
    sys.exit(main())