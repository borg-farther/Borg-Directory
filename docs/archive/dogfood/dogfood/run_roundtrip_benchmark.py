#!/usr/bin/env python3
"""Round-trip quality benchmark for borg pack format."""

import os
import sys
import json
import subprocess
import re
from pathlib import Path
from difflib import SequenceMatcher, unified_diff
from datetime import datetime

# Add borg to path
sys.path.insert(0, '/root/hermes-workspace/borg')

import yaml as pyyaml
from borg.core.generator import generate_rules
try:
    from borg.core.openclaw_converter import convert_pack_to_openclaw_ref
    HAS_OPENCLAW = True
except ImportError:
    HAS_OPENCLAW = False
    print("WARNING: openclaw_converter not available")

BASE = Path('/root/hermes-workspace/borg/dogfood/roundtrip_data')
ORIGINALS = BASE / 'cursorrules_originals'
PACKS = BASE / 'cursorrules_packs'
ROUNDTRIPPED = BASE / 'cursorrules_roundtripped'
SKILLS_ORIG = BASE / 'skills_originals'
SKILLS_PACKS = BASE / 'skills_packs'
SKILLS_RT = BASE / 'skills_roundtripped'

results = []
skill_results = []


def extract_semantic_units(text):
    """Extract meaningful semantic units from text for comparison."""
    units = {
        'rules': [],
        'code_blocks': [],
        'anti_patterns': [],
        'links': [],
        'headers': [],
        'bullet_points': [],
    }
    
    lines = text.split('\n')
    in_code_block = False
    code_block = []
    
    for line in lines:
        stripped = line.strip()
        
        # Code blocks
        if stripped.startswith('```'):
            if in_code_block:
                units['code_blocks'].append('\n'.join(code_block))
                code_block = []
                in_code_block = False
            else:
                in_code_block = True
            continue
        
        if in_code_block:
            code_block.append(stripped)
            continue
        
        # Headers
        if stripped.startswith('#'):
            units['headers'].append(stripped.lstrip('#').strip())
            continue
        
        # Links
        urls = re.findall(r'https?://[^\s\)]+', stripped)
        units['links'].extend(urls)
        
        # Anti-patterns (lines with NOT, Don't, Avoid, Never)
        if any(kw in stripped for kw in ['NOT', "Don't", "don't", 'Avoid', 'avoid', 'Never', 'never']):
            units['anti_patterns'].append(stripped.lstrip('- '))
        
        # Bullet points / rules
        if stripped.startswith('- ') or stripped.startswith('* '):
            units['bullet_points'].append(stripped[2:])
    
    return units


def score_semantic_preservation(original_text, roundtripped_text):
    """Score how well semantic content was preserved."""
    orig_units = extract_semantic_units(original_text)
    rt_units = extract_semantic_units(roundtripped_text)
    
    scores = {}
    details = {}
    
    for category in orig_units:
        orig_items = orig_units[category]
        rt_items = rt_units[category]
        
        if not orig_items:
            continue
        
        # For each original item, check if something similar exists in roundtripped
        preserved = 0
        lost = []
        for orig_item in orig_items:
            best_match = 0
            for rt_item in rt_items:
                ratio = SequenceMatcher(None, orig_item.lower(), rt_item.lower()).ratio()
                best_match = max(best_match, ratio)
            
            if best_match >= 0.6:  # 60% similarity threshold
                preserved += 1
            else:
                lost.append(orig_item[:80])
        
        score = preserved / len(orig_items) * 100
        scores[category] = score
        details[category] = {
            'original_count': len(orig_items),
            'preserved': preserved,
            'lost_count': len(orig_items) - preserved,
            'lost_items': lost[:5],  # Cap at 5 examples
            'score': score,
        }
    
    # Overall text similarity
    text_sim = SequenceMatcher(None, original_text, roundtripped_text).ratio() * 100
    
    # Weighted overall score
    weights = {
        'bullet_points': 3,
        'headers': 2,
        'anti_patterns': 2,
        'code_blocks': 1.5,
        'links': 1,
        'rules': 1,
    }
    
    total_weight = 0
    weighted_score = 0
    for cat, score in scores.items():
        w = weights.get(cat, 1)
        weighted_score += score * w
        total_weight += w
    
    overall = weighted_score / total_weight if total_weight > 0 else text_sim
    
    return {
        'overall_score': round(overall, 1),
        'text_similarity': round(text_sim, 1),
        'category_scores': scores,
        'details': details,
    }


def run_cursorrules_benchmark():
    """Run round-trip benchmark on all .cursorrules files."""
    print("\n=== CURSORRULES ROUND-TRIP BENCHMARK ===\n")
    
    for cr_file in sorted(ORIGINALS.glob('*.cursorrules')):
        name = cr_file.stem
        print(f"Testing: {name}")
        
        # Read original
        original = cr_file.read_text()
        
        # Convert to pack via borg CLI
        try:
            result = subprocess.run(
                ['borg', 'convert', str(cr_file), '--format', 'cursorrules'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                print(f"  ERROR converting: {result.stderr}")
                results.append({'name': name, 'error': result.stderr, 'overall_score': 0})
                continue
            
            pack_yaml = result.stdout
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({'name': name, 'error': str(e), 'overall_score': 0})
            continue
        
        # Save pack
        pack_path = PACKS / f'{name}.yaml'
        pack_path.write_text(pack_yaml)
        
        # Load pack and generate back to cursorrules
        try:
            pack = pyyaml.safe_load(pack_path.read_text())
            roundtripped = generate_rules(pack, 'cursorrules')
        except Exception as e:
            print(f"  ERROR generating: {e}")
            results.append({'name': name, 'error': str(e), 'overall_score': 0})
            continue
        
        # Save roundtripped
        rt_path = ROUNDTRIPPED / f'{name}.cursorrules'
        rt_path.write_text(roundtripped)
        
        # Score
        score_data = score_semantic_preservation(original, roundtripped)
        score_data['name'] = name
        score_data['original_size'] = len(original)
        score_data['roundtripped_size'] = len(roundtripped)
        
        # Save diff
        diff = '\n'.join(unified_diff(
            original.splitlines(), roundtripped.splitlines(),
            fromfile=f'original/{name}', tofile=f'roundtripped/{name}',
            lineterm=''
        ))
        diff_path = BASE / f'diffs/{name}.diff'
        diff_path.parent.mkdir(exist_ok=True)
        diff_path.write_text(diff)
        
        results.append(score_data)
        print(f"  Overall: {score_data['overall_score']}% | Text similarity: {score_data['text_similarity']}%")
        for cat, s in score_data['category_scores'].items():
            print(f"    {cat}: {s:.0f}%")


def run_skills_benchmark():
    """Run round-trip benchmark on SKILL.md files."""
    print("\n=== SKILL.MD ROUND-TRIP BENCHMARK ===\n")
    
    skills_dir = Path.home() / '.hermes' / 'skills'
    if not skills_dir.exists():
        print("No skills directory found")
        return
    
    # Pick 5 skills that have SKILL.md
    available = [d.name for d in skills_dir.iterdir() if d.is_dir() and (d / 'SKILL.md').exists()]
    target_skills = ['unit-testing', 'api-integration', 'borg-auto-observe', 'dogfood', 'guild-autopilot']
    selected = [s for s in target_skills if s in available]
    
    # Fill remaining slots
    for s in available:
        if len(selected) >= 5:
            break
        if s not in selected:
            selected.append(s)
    
    selected = selected[:5]
    print(f"Testing skills: {selected}")
    
    for skill_name in selected:
        skill_path = skills_dir / skill_name / 'SKILL.md'
        if not skill_path.exists():
            print(f"  {skill_name}: SKILL.md not found")
            continue
        
        print(f"\nTesting skill: {skill_name}")
        original = skill_path.read_text()
        
        # Copy original
        (SKILLS_ORIG / f'{skill_name}.md').write_text(original)
        
        # Convert to pack
        try:
            result = subprocess.run(
                ['borg', 'convert', str(skill_path), '--format', 'skill'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                print(f"  ERROR converting: {result.stderr}")
                skill_results.append({'name': skill_name, 'error': result.stderr, 'overall_score': 0})
                continue
            
            pack_yaml = result.stdout
        except Exception as e:
            print(f"  ERROR: {e}")
            skill_results.append({'name': skill_name, 'error': str(e), 'overall_score': 0})
            continue
        
        # Save pack
        pack_path = SKILLS_PACKS / f'{skill_name}.yaml'
        pack_path.write_text(pack_yaml)
        
        # Try to export back
        try:
            pack = pyyaml.safe_load(pack_path.read_text())
            
            # Try openclaw converter
            if HAS_OPENCLAW:
                roundtripped = convert_pack_to_openclaw_ref(pack)
            else:
                # Fall back to skill format generation
                roundtripped = generate_rules(pack, 'cursorrules')
        except Exception as e:
            # Try another format
            try:
                pack = pyyaml.safe_load(pack_path.read_text())
                roundtripped = generate_rules(pack, 'cursorrules')
            except Exception as e2:
                print(f"  ERROR generating: {e} / {e2}")
                skill_results.append({'name': skill_name, 'error': str(e), 'overall_score': 0})
                continue
        
        # Save roundtripped
        rt_path = SKILLS_RT / f'{skill_name}.md'
        rt_path.write_text(roundtripped)
        
        # Score
        score_data = score_semantic_preservation(original, roundtripped)
        score_data['name'] = skill_name
        score_data['original_size'] = len(original)
        score_data['roundtripped_size'] = len(roundtripped)
        
        skill_results.append(score_data)
        print(f"  Overall: {score_data['overall_score']}% | Text similarity: {score_data['text_similarity']}%")


def generate_report():
    """Generate the quality report."""
    report = []
    report.append("# Borg Pack Round-Trip Quality Report")
    report.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Borg version: 3.1.0")
    report.append("")
    
    # Summary
    cr_scores = [r['overall_score'] for r in results if 'error' not in r]
    sk_scores = [r['overall_score'] for r in skill_results if 'error' not in r]
    all_scores = cr_scores + sk_scores
    
    overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
    
    report.append("## Executive Summary")
    report.append("")
    report.append(f"**Overall Round-Trip Fidelity: {overall_avg:.1f}%**")
    report.append("")
    if cr_scores:
        report.append(f"- Cursorrules avg: {sum(cr_scores)/len(cr_scores):.1f}% ({len(cr_scores)} files)")
    if sk_scores:
        report.append(f"- SKILL.md avg: {sum(sk_scores)/len(sk_scores):.1f}% ({len(sk_scores)} files)")
    report.append("")
    
    # Cursorrules results table
    report.append("## Cursorrules Round-Trip Results")
    report.append("")
    report.append("| File | Overall | Text Sim | Headers | Bullets | Anti-patterns | Code | Links |")
    report.append("|------|---------|----------|---------|---------|---------------|------|-------|")
    
    for r in sorted(results, key=lambda x: x.get('overall_score', 0), reverse=True):
        if 'error' in r:
            report.append(f"| {r['name']} | ERROR | - | - | - | - | - | - |")
            continue
        
        cats = r.get('category_scores', {})
        report.append(
            f"| {r['name']} "
            f"| {r['overall_score']}% "
            f"| {r['text_similarity']}% "
            f"| {cats.get('headers', '-'):.0f}% " if isinstance(cats.get('headers'), (int, float)) else f"| {r['name']} | {r['overall_score']}% | {r['text_similarity']}% | - "
        )
    
    # Rebuild table more carefully
    report = report[:report.index("| File | Overall | Text Sim | Headers | Bullets | Anti-patterns | Code | Links |")]
    report.append("| File | Overall | Text Sim | Headers | Bullets | Anti-patterns | Code | Links |")
    report.append("|------|---------|----------|---------|---------|---------------|------|-------|")
    
    for r in sorted(results, key=lambda x: x.get('overall_score', 0), reverse=True):
        if 'error' in r:
            report.append(f"| {r['name']} | ERROR | - | - | - | - | - | - |")
            continue
        
        cats = r.get('category_scores', {})
        def fmt(key):
            v = cats.get(key)
            return f"{v:.0f}%" if isinstance(v, (int, float)) else "-"
        
        report.append(
            f"| {r['name']} | {r['overall_score']}% | {r['text_similarity']}% "
            f"| {fmt('headers')} | {fmt('bullet_points')} | {fmt('anti_patterns')} "
            f"| {fmt('code_blocks')} | {fmt('links')} |"
        )
    
    report.append("")
    
    # Skills results
    if skill_results:
        report.append("## SKILL.md Round-Trip Results")
        report.append("")
        report.append("| Skill | Overall | Text Sim | Headers | Bullets | Code |")
        report.append("|-------|---------|----------|---------|---------|------|")
        
        for r in sorted(skill_results, key=lambda x: x.get('overall_score', 0), reverse=True):
            if 'error' in r:
                report.append(f"| {r['name']} | ERROR | - | - | - | - |")
                continue
            
            cats = r.get('category_scores', {})
            def fmt(key):
                v = cats.get(key)
                return f"{v:.0f}%" if isinstance(v, (int, float)) else "-"
            
            report.append(
                f"| {r['name']} | {r['overall_score']}% | {r['text_similarity']}% "
                f"| {fmt('headers')} | {fmt('bullet_points')} | {fmt('code_blocks')} |"
            )
        report.append("")
    
    # Analysis: What survives well
    report.append("## Analysis: What Survives Well")
    report.append("")
    
    # Aggregate category scores
    all_cats = {}
    for r in results + skill_results:
        if 'error' in r:
            continue
        for cat, score in r.get('category_scores', {}).items():
            all_cats.setdefault(cat, []).append(score)
    
    report.append("| Content Type | Avg Preservation | Sample Count |")
    report.append("|-------------|-----------------|--------------|")
    for cat in sorted(all_cats.keys(), key=lambda c: sum(all_cats[c])/len(all_cats[c]), reverse=True):
        scores = all_cats[cat]
        avg = sum(scores) / len(scores)
        report.append(f"| {cat} | {avg:.1f}% | {len(scores)} |")
    
    report.append("")
    
    # What gets lost
    report.append("## Analysis: What Gets Lost")
    report.append("")
    
    all_lost = {}
    for r in results + skill_results:
        if 'error' in r:
            continue
        for cat, detail in r.get('details', {}).items():
            if detail['lost_count'] > 0:
                all_lost.setdefault(cat, []).extend(detail.get('lost_items', []))
    
    for cat, items in sorted(all_lost.items()):
        if items:
            report.append(f"### Lost {cat}")
            for item in items[:8]:
                report.append(f"- `{item}`")
            report.append("")
    
    # Conclusions
    report.append("## Conclusions & Recommendations")
    report.append("")
    
    if overall_avg >= 80:
        report.append(f"The borg pack format achieves **{overall_avg:.1f}%** round-trip fidelity, which is GOOD.")
    elif overall_avg >= 60:
        report.append(f"The borg pack format achieves **{overall_avg:.1f}%** round-trip fidelity, which is ACCEPTABLE.")
    else:
        report.append(f"The borg pack format achieves **{overall_avg:.1f}%** round-trip fidelity, which NEEDS IMPROVEMENT.")
    
    report.append("")
    report.append("Key findings:")
    
    # Find best/worst categories
    if all_cats:
        best_cat = max(all_cats.keys(), key=lambda c: sum(all_cats[c])/len(all_cats[c]))
        worst_cat = min(all_cats.keys(), key=lambda c: sum(all_cats[c])/len(all_cats[c]))
        best_avg = sum(all_cats[best_cat]) / len(all_cats[best_cat])
        worst_avg = sum(all_cats[worst_cat]) / len(all_cats[worst_cat])
        
        report.append(f"- Best preserved: **{best_cat}** ({best_avg:.0f}%)")
        report.append(f"- Worst preserved: **{worst_cat}** ({worst_avg:.0f}%)")
    
    report.append(f"- Total files tested: {len(results) + len(skill_results)}")
    errors = sum(1 for r in results + skill_results if 'error' in r)
    if errors:
        report.append(f"- Conversion errors: {errors}")
    
    report.append("")
    report.append("## Files Generated")
    report.append("")
    report.append("- Original cursorrules: `roundtrip_data/cursorrules_originals/`")
    report.append("- Pack YAML files: `roundtrip_data/cursorrules_packs/`")
    report.append("- Round-tripped files: `roundtrip_data/cursorrules_roundtripped/`")
    report.append("- Diffs: `roundtrip_data/diffs/`")
    report.append("- Skills data: `roundtrip_data/skills_*/`")
    
    return '\n'.join(report)


if __name__ == '__main__':
    run_cursorrules_benchmark()
    run_skills_benchmark()
    
    report = generate_report()
    
    report_path = Path('/root/hermes-workspace/borg/dogfood/roundtrip_quality.md')
    report_path.parent.mkdir(exist_ok=True)
    report_path.write_text(report)
    
    print(f"\n\nReport saved to: {report_path}")
    print(f"\nOverall scores:")
    for r in results:
        print(f"  {r.get('name', '?')}: {r.get('overall_score', 'ERROR')}%")
    for r in skill_results:
        print(f"  SKILL/{r.get('name', '?')}: {r.get('overall_score', 'ERROR')}%")
