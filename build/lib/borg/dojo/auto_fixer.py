"""
Borg Dojo — AutoFixer.
Applies targeted fixes to skills based on SessionAnalysis. Implements the
patch/create/evolve/log decision tree with atomic rollback support.

Public API:
  AutoFixer.recommend(analysis) -> List[FixAction]
  AutoFixer.apply_fix(fix) -> FixAction
  AutoFixer.rollback_fix(fix) -> bool
  AutoFixer.get_fix_history() -> List[FixAction]
"""

import logging
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from borg.dojo.data_models import FixAction, SessionAnalysis, SkillGap, ToolMetric

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fix strategies — 8 categories
# ---------------------------------------------------------------------------

FIX_STRATEGIES: Dict[str, tuple] = {
    "path_not_found": (
        "Add path validation before file operations. Check `os.path.exists()` first.",
        "## Pre-flight Checks\n- Verify path exists before ANY file operation\n"
        "- Search ~/Documents/, ./, ~/ if not found\n- Ask user if ambiguous\n",
    ),
    "timeout": (
        "Add retry with exponential backoff (5s, 10s, 20s). Fall back after 3 failures.",
        "## Timeout Handling\n- Set initial timeout to 10s\n"
        "- Retry 3x with 2x backoff\n- Fall back to alternative approach\n",
    ),
    "permission_denied": (
        "Check permissions before operations. Suggest chmod/sudo with explanation.",
        "## Permission Checks\n- Verify file permissions before read/write\n"
        "- Explain the permission issue clearly\n- Never auto-sudo without confirmation\n",
    ),
    "command_not_found": (
        "Verify command exists with `which` before execution. Suggest install if missing.",
        "## Command Verification\n- Run `which <command>` before use\n"
        "- Suggest installation if missing\n- Try alternatives (python3 vs python)\n",
    ),
    "rate_limit": (
        "Parse retry-after header. Use exponential backoff. Fall back to alternative source.",
        "## Rate Limiting\n- Check for 429 + retry-after header\n"
        "- Wait before retrying\n- Fall back to alternative source\n",
    ),
    "syntax_error": (
        "Validate syntax before execution. Use ast.parse() for Python, shellcheck for bash.",
        "## Syntax Validation\n- Pre-validate code before execution\n"
        "- Show specific error location with context\n",
    ),
    "network": (
        "Check connectivity before network operations. Add timeout and retry logic.",
        "## Network Resilience\n- Verify connectivity first\n"
        "- Set explicit timeouts\n- Retry with backoff on transient failures\n",
    ),
    "generic": (
        "Add try/except with clear error messages and user guidance.",
        "## Error Handling\n- Wrap operations in try/except\n"
        "- Log clear error messages\n- Suggest actionable next steps\n",
    ),
}

SKILL_SEARCH_DIRS = [Path.home() / ".hermes" / "skills"]
SUCCESS_RATE_PATCH_THRESHOLD = 0.60
SKILL_CREATE_THRESHOLD = 3


# ---------------------------------------------------------------------------
# AutoFixer
# ---------------------------------------------------------------------------

class AutoFixer:
    """Applies fixes with atomic rollback. Decision tree (BORG_DOJO_SPEC.md §4.5):

    Existing skill + success > 60%  → patch
    Existing skill + success < 60%  → evolve (defer)
    No skill + 3+ requests          → create
    No skill + <3 requests          → log
    """

    BACKUP_DIR = Path.home() / ".hermes" / "borg" / "dojo_backups"

    def __init__(self, skill_dirs: Optional[List[Path]] = None):
        self._skill_dirs = skill_dirs or SKILL_SEARCH_DIRS
        self._fix_history: List[FixAction] = []

    def recommend(self, analysis: SessionAnalysis) -> List[FixAction]:
        """Ranked FixAction recommendations from SessionAnalysis."""
        recs: List[FixAction] = []
        for metric in analysis.weakest_tools:
            fix = self._recommend_for_tool(metric)
            if fix:
                recs.append(fix)
        for gap in analysis.skill_gaps:
            fix = self._recommend_for_gap(gap)
            if fix:
                recs.append(fix)
        recs.sort(key=lambda f: f.priority, reverse=True)
        return recs

    def apply_fix(self, fix: FixAction) -> FixAction:
        """Apply a fix with atomic rollback. Updates fix.applied, fix.success, fix.rollback_path."""
        fix.applied = fix.success = False
        if fix.action == "patch":
            return self._apply_patch_fix(fix)
        if fix.action == "create":
            return self._apply_create_fix(fix)
        if fix.action == "evolve":
            fix.applied = fix.success = True
            logger.info("FixAction '%s' marked as evolve (deferred)", fix.target_skill)
            return fix
        if fix.action == "log":
            fix.applied = fix.success = True
            return fix
        logger.warning("Unknown fix action '%s'", fix.action)
        return fix

    def rollback_fix(self, fix: FixAction) -> bool:
        """Restore skill from backup. Returns True on success."""
        if not fix.rollback_path or not Path(fix.rollback_path).exists():
            return False
        rp = Path(fix.rollback_path)
        if fix.action == "patch":
            sp = self._find_skill(fix.target_skill)
            if not sp:
                return False
            try:
                shutil.copy2(rp, sp / "SKILL.md")
                return True
            except Exception as e:
                logger.error("Rollback patch failed: %s", e)
                return False
        if fix.action == "create":
            sn = self._normalize_skill_name(fix.target_skill)
            for d in self._skill_dirs:
                if not d.exists():
                    continue
                p = d / sn
                if p.exists():
                    try:
                        shutil.rmtree(p)
                        return True
                    except Exception as e:
                        logger.error("Rollback create failed: %s", e)
                        return False
            return False
        return False

    def get_fix_history(self) -> List[FixAction]:
        return list(self._fix_history)

    def clear_history(self) -> None:
        self._fix_history.clear()

    # -----------------------------------------------------------------------
    # Decision tree
    # -----------------------------------------------------------------------

    def _recommend_for_tool(self, metric: ToolMetric) -> Optional[FixAction]:
        sp = self._find_skill(metric.tool_name)
        if not sp:
            return None
        if metric.success_rate > SUCCESS_RATE_PATCH_THRESHOLD:
            strat = FIX_STRATEGIES.get(metric.top_error_category, FIX_STRATEGIES["generic"])
            patch = f"\n<!-- AUTO-FIX: {metric.top_error_category} -->\n{strat[1]}"
            reason = (f"Tool '{metric.tool_name}' has {metric.success_rate:.0%} success "
                      f"(above threshold). Patching for {metric.top_error_category}.")
            fix = FixAction(action="patch", target_skill=metric.tool_name,
                            priority=self._priority(metric, False), reason=reason,
                            fix_content=patch)
        else:
            reason = (f"Tool '{metric.tool_name}' has {metric.success_rate:.0%} success "
                      "(below threshold). Deferring for deep evolution.")
            fix = FixAction(action="evolve", target_skill=metric.tool_name,
                            priority=self._priority(metric, False), reason=reason,
                            fix_content="")
        self._fix_history.append(fix)
        return fix

    def _recommend_for_gap(self, gap: SkillGap) -> Optional[FixAction]:
        if gap.request_count >= SKILL_CREATE_THRESHOLD:
            if gap.existing_skill:
                sp = self._find_skill(gap.existing_skill)
                if sp:
                    reason = (f"Gap '{gap.capability}' requested {gap.request_count}x "
                              f"despite existing skill '{gap.existing_skill}'.")
                    patch = f"\n<!-- AUTO-FIX: gap '{gap.capability}' -->\n"
                    patch += self._strategy_for_cap(gap.capability)[1]
                    fix = FixAction(action="patch", target_skill=gap.existing_skill,
                                    priority=min(gap.request_count * 10.0, 100.0),
                                    reason=reason, fix_content=patch)
                    self._fix_history.append(fix)
                    return fix
            return self._create_new_skill(gap)
        reason = (f"Gap '{gap.capability}' has {gap.request_count} requests "
                  f"(below {SKILL_CREATE_THRESHOLD}). Logging for future.")
        fix = FixAction(action="log", target_skill=gap.capability,
                        priority=gap.request_count * 5.0, reason=reason, fix_content="")
        self._fix_history.append(fix)
        return fix

    def _create_new_skill(self, gap: SkillGap) -> FixAction:
        sn = self._normalize_skill_name(gap.capability)
        strat = self._strategy_for_cap(gap.capability)
        content = f"# {gap.capability.replace('-', ' ').title()}\n\n"
        content += f"**Auto-generated** — confidence: {gap.confidence:.0%}\n"
        content += f"\nSessions: {len(gap.session_ids)}\n\n{strat[1]}\n"
        content += "\n## Usage\nDescribe how to use this capability.\n"
        reason = (f"Gap '{gap.capability}' requested {gap.request_count}x "
                  f"(above threshold). Creating new skill.")
        fix = FixAction(action="create", target_skill=sn,
                        priority=min(gap.request_count * 15.0, 100.0),
                        reason=reason, fix_content=content)
        self._fix_history.append(fix)
        return fix

    # -----------------------------------------------------------------------
    # Skill file operations
    # -----------------------------------------------------------------------

    def _find_skill(self, ident: str) -> Optional[Path]:
        norm = self._normalize_skill_name(ident)
        for base in self._skill_dirs:
            if not base.exists():
                continue
            # Direct match
            p = base / norm / "SKILL.md"
            if p.exists():
                return p.parent
            # Subdirectory match
            for sub in base.iterdir():
                if sub.is_dir():
                    sm = sub / "SKILL.md"
                    if sm.exists() and (sub.name == norm or ident.lower() in sub.name.lower()):
                        return sub
            # Recursive
            for sm in base.rglob("SKILL.md"):
                if norm.lower() in str(sm).lower():
                    return sm.parent
        return None

    def _normalize_skill_name(self, name: str) -> str:
        return name.lower().replace(" ", "-").replace("_", "-")

    def _strategy_for_cap(self, cap: str):
        cap_lower = cap.lower()
        for key, strat in FIX_STRATEGIES.items():
            if key in cap_lower:
                return strat
        return FIX_STRATEGIES["generic"]

    def _priority(self, metric: ToolMetric, gap: bool) -> float:
        if gap:
            return min(metric.failed_calls * 10.0, 100.0)
        return min((1.0 - metric.success_rate) * (metric.failed_calls / max(metric.total_calls, 1)) * 100.0, 100.0)

    # -----------------------------------------------------------------------
    # Apply / rollback
    # -----------------------------------------------------------------------

    def _apply_patch_fix(self, fix: FixAction) -> FixAction:
        sp = self._find_skill(fix.target_skill)
        if not sp:
            logger.error("Skill not found for patch: '%s'", fix.target_skill)
            return fix
        sm = sp / "SKILL.md"
        if not sm.exists():
            logger.error("SKILL.md not found: '%s'", sm)
            return fix

        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        bp = self.BACKUP_DIR / f"{fix.target_skill}_{int(time.time())}.md"
        shutil.copy2(sm, bp)
        fix.backup_content = sm.read_text()
        fix.rollback_path = str(bp)

        try:
            sm.write_text(sm.read_text() + fix.fix_content)
            if not self._validate_skill_yaml(sm):
                shutil.copy2(bp, sm)
                fix.applied = fix.success = False
                logger.error("YAML validation failed for '%s', rolled back", sm)
                return fix
            fix.applied = fix.success = True
            logger.info("Patched '%s'", sm)
        except Exception as e:
            if bp.exists():
                shutil.copy2(bp, sm)
            fix.applied = fix.success = False
            logger.error("Exception during patch of '%s': %s", sm, e)
        return fix

    def _apply_create_fix(self, fix: FixAction) -> FixAction:
        sn = self._normalize_skill_name(fix.target_skill)
        base = None
        for d in self._skill_dirs:
            if d.exists():
                base = d
                break
        if not base:
            logger.error("No skill directory found");
            return fix

        sp = base / sn
        if sp.exists():
            logger.error("Skill directory already exists: '%s'", sp)
            fix.success = False
            return fix

        self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        marker = self.BACKUP_DIR / f"_create_{sn}_{int(time.time())}.marker"

        try:
            sp.mkdir(parents=True)
            sm = sp / "SKILL.md"
            sm.write_text(fix.fix_content)
            if not self._validate_skill_yaml(sm):
                shutil.rmtree(sp)
                fix.applied = fix.success = False
                logger.error("YAML validation failed for new skill '%s'", sm)
                return fix
            fix.backup_content = ""
            fix.rollback_path = str(marker)
            fix.applied = fix.success = True
            logger.info("Created new skill at '%s'", sm)
        except Exception as e:
            if sp.exists():
                shutil.rmtree(sp)
            fix.applied = fix.success = False
            logger.error("Exception during create of '%s': %s", sp, e)
        return fix

    # -----------------------------------------------------------------------
    # YAML validation
    # -----------------------------------------------------------------------

    def _validate_skill_yaml(self, skill_md: Path) -> bool:
        """Validate YAML frontmatter. Returns True if valid or absent."""
        try:
            content = skill_md.read_text()
            if not content.strip():
                return True
            stripped = content.strip()
            if not stripped.startswith("---"):
                return True  # Pure markdown
            # Find closing ---
            first_nl = stripped.find("\n")
            if first_nl == -1:
                return True
            rest = stripped[first_nl + 1:]
            close = rest.find("\n---")
            if close == -1:
                logger.warning("Incomplete YAML frontmatter (no closing '---') in '%s'", skill_md)
                return False
            frontmatter = rest[:close]
            yaml.safe_load(frontmatter)
            return True
        except yaml.YAMLError as e:
            logger.warning("YAML validation error in '%s': %s", skill_md, e)
            return False
