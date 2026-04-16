"""Format Borg results for agent consumption. One fix, dead-end guidance, attribution."""
import json
def format_response(traces, query="", technology=""):
    if not traces:
        return "BORG: No matches found.\nProceed with your own analysis. If you fix it, the solution will be saved to help future agents."
    top=traces[0]; n=len(traces)
    rc=(top.get('root_cause','') or '').strip()
    ap=(top.get('approach_summary','') or '').strip()
    de=(top.get('dead_ends','') or '').strip()
    tech=top.get('technology',technology or 'unknown')
    src=top.get('source','organic')
    sl="verified in real sessions" if src not in ('seed','curated','golden_seed') else "from curated knowledge"
    lines=[f"BORG: {n} match{'es' if n>1 else ''} found\n",f"RECOMMENDED FIX: {ap[:300]}",f"ROOT CAUSE: {rc[:200]}"]
    if de and de not in ('[]','','""'):
        try:
            ends=json.loads(de)
            if isinstance(ends,list):
                for e in ends[:3]: lines.append(f"SKIP: {e}")
        except: pass
    lines.append(f"\nConfidence: {sl} | {tech}")
    lines.append("Source: Borg collective  error knowledge from real agent sessions")
    if n>=2:
        alt=(traces[1].get('approach_summary','') or '').strip()
        if alt and alt!=ap: lines.append(f"\nAlternative: {alt[:120]}")
    return '\n'.join(lines)
