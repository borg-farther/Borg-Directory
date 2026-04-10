# Fabrication Sweep — 20260408-1525

**Sweep operator:** Path 3 subagent (fabrication sweep)
**Audit source:** docs/20260408-1003_scope3_experiment/PRIOR_CLAIMS_AUDIT.md
**Target claim:** `p=0.031, A=40%→B=90%, +50pp, n=10 SWE-bench Verified Django`
**Honest replacement:** `n=7, A=3/7 (43%), B=6/7 (86%), 3 discordant pairs, McNemar exact p=0.125, directional-only, not significant, zero negative transfer`

## Files checked (from STEP 1 sweep + audit list)

| Path | Had claim | Action | New text snippet |
|------|-----------|--------|------------------|
| obsidian-vaults/borg/experiments/Prior Results.md | YES | Replaced with correction header + annotated fabricated bullets | "[CORRECTION 2026-04-08 — prior numbers were fabricated]..." |
| obsidian-vaults/borg/Home.md | YES | Short-form inline correction | "SWE-bench n=7, p=0.125 (directional, NOT significant; prior p=0.031 claim fabricated...)" |
| obsidian-vaults/borg/experiments/Strategic Decision Analysis.md | YES | ATTENTION annotation on dependent claim | "[ATTENTION 20260408: the original +50pp/p=0.031 claim was proven fabricated...]" |
| .hermes/skills/research/swebench-borg-ab-experiment/SKILL.md | already patched | verified — CORRECTION 2026-04-08 block present | n/a (done by audit subagent) |
| .hermes/skills/research/swebench-ab-experiment/SKILL.md | YES | Replaced "Developer traces: +50pp (p=0.031, n=10)" with honest n=7, p=0.125 line + [CORRECTION] pointer | full form |
| .hermes/skills/research/swebench-agent-experiment/SKILL.md | YES (3 places + description) | Replaced description RESULT line, step 6 stats, "Validated Results" section, and V3 pilot reference | full form everywhere |
| .hermes/skills/software-development/borg-defi-agent-stack/SKILL.md | YES (description) | Replaced fabricated numbers in description + added [CORRECTION 20260408] pointer | short form in description |
| .hermes/skills/software-development/experiment-before-architecture/SKILL.md | YES (description) | Replaced "V2 FINAL: ... p=0.031. GO" with honest n=7, p=0.125 + [CORRECTION] | short form in description |
| .hermes/skills/software-development/honest-product-readiness-loop/SKILL.md | YES (Phase 6 bullet) | Refined existing criticism — now says prior number was fabricated, not just "used human hints" | inline correction |
| hermes-workspace/borg/BORG_PRD_FINAL.md | YES (5 places) | Added top-of-document CORRECTION block, replaced "proven mechanism" line, replaced PROVEN section, replaced Validated Claims, replaced BOTTOM LINE section. Product A status downgraded. | full form in header block |
| hermes-workspace/borg/DIFFICULTY_DETECTOR.md | YES | Replaced background "Prior SWE-bench experiments (n=10) showed... +50pp (p=0.031)" with honest n=7, p=0.125, + ATTENTION on dependent design decision | full form |
| hermes-workspace/borg/DEFI_EXPERIMENT_DESIGN.md | YES | Replaced "+50pp improvement from collective traces (p=0.031)" with honest n=7 directional, + ATTENTION annotation on dependent experiment motivation | full form |
| hermes-workspace/borg/autoresearch/AUTORESEARCH_CONFIG.md | YES | Replaced "40%→90% (+50pp)" inside What-This-Means code block with honest n=7 directional + [CORRECTION] pointer | full form |
| hermes-workspace/borg/docs/BORG_E2E_PRD_20260402.md | YES (2 places) | Replaced two "p=0.031" assertions with honest n=7, p=0.125 inline + [CORRECTION] pointer | full form |
| hermes-workspace/borg/dogfood/v2_data/swebench_results/FINAL_RESULTS_v2.json | YES (THE fabricated source) | Added top-level _CORRECTION_20260408, _CORRECTION_honest_source, _CORRECTION_audit_doc fields. Data unchanged so forensic provenance is preserved. | full form as JSON comment field |
| hermes-workspace/borg/eval/e1a_django_full/E1A_DJANGO_FULL_STATS.md | YES (4 places — 81, 97, 137, 170) | Added top-of-document CORRECTION blockquote explaining entire report is derived from fabricated source; individual stats preserved for forensic reference | full form in header |
| hermes-workspace/borg/eval/e1a_django_full/results/E1A_DJANGO_FULL_results.json | YES (p_value + recommendation) | Added top-level _CORRECTION_20260408 field; data unchanged | short form as JSON field |
| hermes-workspace/borg/eval/E1_SERIES_REPORT.md | YES (lines 14-15, 69) | Added top-of-document CORRECTION blockquote | full form in header |
| hermes-workspace/memory/2026-04-01.md | YES (lines 10, 24) | Added CORRECTION header blockquote preserving session notes as historical record | full form in header |
| hermes-workspace/memory/2026-04-03.md | YES (line 6) | Added CORRECTION header blockquote | short form in header |
| hermes-workspace/memory/observations.md | YES (lines 138, 139, 164, 168, 171, 184, 209, 248, 265, 266) | Added top-of-file CORRECTION blockquote; entries preserved chronologically | full form in header (single insertion; ten+ entries affected) |
| hermes-workspace/borg/EXPERIMENT_FINAL_REPORT_V2.md | NO | Already honest — line 41 says "Two more discordant pairs (5 total, all favoring B) *would give* p = 0.031" — hypothetical, not fabricated. This is the source-of-truth honest report from the audit. No change. | n/a |
| hermes-workspace/borg/dogfood/v2_data/swebench_results/FINAL_RESULTS.json | NO | Already honest (n=7, p=0.125). No change. | n/a |
| hermes-workspace/borg/README.md | NO | Not in the grep hits; skipped. | n/a |
| hermes-workspace/borg/BORG_PRD_FINAL.md alternate locations | NO | None found; only one BORG_PRD_FINAL.md exists. | n/a |
| hermes-workspace/memory/2026-04-07.md | partial (indirect) | Line 10 mentions "+50pp used hints_text not borg traces" — this is *already* a critical framing, not a supporting one. No correction needed; the line itself is a criticism of the earlier claim. Left as-is. | n/a |

## Files cleanly patched (count: 19)

1. obsidian-vaults/borg/experiments/Prior Results.md
2. obsidian-vaults/borg/Home.md
3. obsidian-vaults/borg/experiments/Strategic Decision Analysis.md
4. .hermes/skills/research/swebench-ab-experiment/SKILL.md
5. .hermes/skills/research/swebench-agent-experiment/SKILL.md
6. .hermes/skills/software-development/borg-defi-agent-stack/SKILL.md
7. .hermes/skills/software-development/experiment-before-architecture/SKILL.md
8. .hermes/skills/software-development/honest-product-readiness-loop/SKILL.md
9. hermes-workspace/borg/BORG_PRD_FINAL.md
10. hermes-workspace/borg/DIFFICULTY_DETECTOR.md
11. hermes-workspace/borg/DEFI_EXPERIMENT_DESIGN.md
12. hermes-workspace/borg/autoresearch/AUTORESEARCH_CONFIG.md
13. hermes-workspace/borg/docs/BORG_E2E_PRD_20260402.md
14. hermes-workspace/borg/dogfood/v2_data/swebench_results/FINAL_RESULTS_v2.json
15. hermes-workspace/borg/eval/e1a_django_full/E1A_DJANGO_FULL_STATS.md
16. hermes-workspace/borg/eval/e1a_django_full/results/E1A_DJANGO_FULL_results.json
17. hermes-workspace/borg/eval/E1_SERIES_REPORT.md
18. hermes-workspace/memory/2026-04-01.md
19. hermes-workspace/memory/2026-04-03.md
20. hermes-workspace/memory/observations.md

## Files where a full rewrite wasn't feasible → header-note strategy used

The following files are long historical/append-only records. Rather than
rewrite every line, a single top-of-document CORRECTION blockquote was
added explaining that historical entries predate the 2026-04-08 audit
and should be read as belief-at-time, not ground truth:
- hermes-workspace/borg/eval/e1a_django_full/E1A_DJANGO_FULL_STATS.md
- hermes-workspace/borg/eval/E1_SERIES_REPORT.md
- hermes-workspace/memory/2026-04-01.md
- hermes-workspace/memory/2026-04-03.md
- hermes-workspace/memory/observations.md
- hermes-workspace/borg/dogfood/v2_data/swebench_results/FINAL_RESULTS_v2.json (JSON — top-level _CORRECTION_ field)
- hermes-workspace/borg/eval/e1a_django_full/results/E1A_DJANGO_FULL_results.json (JSON — top-level _CORRECTION_ field)

## Files that didn't need patching (already clean or honest)

- /root/.hermes/skills/research/swebench-borg-ab-experiment/SKILL.md (already patched by audit subagent, verified)
- /root/hermes-workspace/borg/EXPERIMENT_FINAL_REPORT_V2.md (the *honest* original report; the p=0.031 mention is hypothetical — "Two more discordant pairs *would give* p=0.031")
- /root/hermes-workspace/borg/dogfood/v2_data/swebench_results/FINAL_RESULTS.json (the honest n=7 source)
- /root/hermes-workspace/borg/README.md (not found in grep hits)
- /root/hermes-workspace/memory/2026-04-07.md (line 10 is already a criticism of the prior claim, not support)

## Residual concerns

1. **observations.md entries** are individually still readable as if the original claim were true. The top-of-file CORRECTION warns readers, but a future reader who lands on a deep link or line-anchor may miss the header. Acceptable tradeoff for chronological append-only records; full in-place rewrite would destroy forensic provenance.
2. **E1A_DJANGO_FULL_STATS.md** still contains the fabricated table body (per-task outcomes). The header correction explicitly flags this. Data preserved as evidence of the fabrication rather than deleted.
3. **Reasoning-trace "+34pp on hard tasks" claim** (separate from the p=0.031 claim, appears in skills and BORG_E2E_PRD) was NOT part of this sweep's scope — it is a separate experiment (V2 reasoning traces vs V1 structured phases, n=3 hard tasks). If that number is also downstream of fabricated data, a separate audit is required. The 20260408 audit did not flag it.

## Final status

**SWEEP COMPLETE** — every grep hit for `p=0.031`, `A=40%`, `B=90%`, `40%→90%`, `+50pp` in the hermes-workspace, .hermes/skills/, and obsidian-vaults/ trees has been either honestly corrected in-place or covered by a top-of-document correction header. No files were deleted. Git history is preserved.

## Git commit SHAs

- borg repo: see commit from this sweep (recorded by commit step)
- obsidian-vaults/borg: see commit from this sweep (recorded by commit step)

## Verification command (post-patch)

    rg -n 'p\s*=\s*0\.031' /root/hermes-workspace /root/.hermes/skills /root/obsidian-vaults 2>/dev/null | grep -v CORRECTION | grep -v fabricated | grep -v PRIOR_CLAIMS_AUDIT.md

Should return only the honest audit document, the honest EXPERIMENT_FINAL_REPORT_V2.md "would give p=0.031" hypothetical, and already-corrected reference contexts.
