"""
Guild Publish Module (T1.8) — standalone publishing tool for guild-v2.

Publish guild artifacts (packs and feedback) to the guild repository via GitHub PR.

Multi-action tool:
  action="publish"   — Validate, privacy-scan, and create a GitHub PR for a pack
  action="list"      — List local artifacts available for publishing
  action="status"    — Check status of a previously created PR

Zero imports from tools.* or guild_mcp.* — stdlib + yaml + json only.
"""

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)

# ============================================================================
# Configurable constants (can be overridden at runtime via module attrs)
# ============================================================================

HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
GUILD_DIR = HERMES_HOME / "guild"
FEEDBACK_DIR = GUILD_DIR / "feedback"
OUTBOX_DIR = GUILD_DIR / "outbox"
EXECUTIONS_DIR = GUILD_DIR / "executions"

DEFAULT_REPO = "bensargotest-sys/guild-packs"
DEFAULT_BRANCH = "main"

# Rate limit: max publishes per agent per day (PRD §12)
MAX_PUBLISHES_PER_DAY = 3

PUBLISH_LOG = GUILD_DIR / "publish_log.jsonl"


# ============================================================================
# Import sibling validation modules with graceful fallbacks
# ============================================================================

try:
    from guild.core.proof_gates import validate_proof_gates
except ImportError:
    def validate_proof_gates(artifact: dict) -> List[str]:
        """Fallback: no-op proof gate validator."""
        return []

try:
    from guild.core.safety import scan_pack_safety
except ImportError:
    def scan_pack_safety(pack: dict) -> List[str]:
        """Fallback: no-op safety scanner."""
        return []

try:
    from guild.core.safety import scan_privacy as _safety_scan_privacy
except ImportError:
    _safety_scan_privacy = None

try:
    from guild.core.privacy import privacy_scan_text, privacy_scan_artifact
except ImportError:
    def privacy_scan_text(text: str) -> Tuple[str, List[str]]:
        """Fallback: no-op text scanner."""
        return text, []
    def privacy_scan_artifact(artifact: dict) -> Tuple[dict, List[str]]:
        """Fallback: no-op artifact scanner."""
        return artifact, []

try:
    from guild.db.store import GuildStore
except ImportError:
    GuildStore = None


# ============================================================================
# Rate limiting
# ============================================================================

def check_rate_limit() -> Tuple[bool, int]:
    """Check if we've exceeded the daily publish limit.

    Returns (allowed: bool, publishes_today: int).
    """
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = 0

    if PUBLISH_LOG.exists():
        for line in PUBLISH_LOG.read_text(encoding="utf-8").strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                if entry.get("date") == today and entry.get("status") == "published":
                    count += 1
            except json.JSONDecodeError:
                continue

    return count < MAX_PUBLISHES_PER_DAY, count


def log_publish(
    artifact_id: str,
    artifact_type: str,
    status: str,
    pr_url: str = "",
    outbox_path: str = "",
) -> None:
    """Append a publish event to the publish log."""
    PUBLISH_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "status": status,
        "pr_url": pr_url,
        "outbox_path": outbox_path,
    }
    with open(PUBLISH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ============================================================================
# GitHub PR creation
# ============================================================================

def create_github_pr(
    artifact: dict,
    artifact_yaml: str,
    artifact_type: str,
    filename: str,
    repo: str = "",
) -> dict:
    """Create a GitHub PR to the guild-packs repo using `gh` CLI.

    Returns dict with keys: success (bool), pr_url (str, on success),
    or error (str, on failure).
    """
    gh_path = shutil.which("gh")
    if not gh_path:
        return {"success": False, "error": "gh CLI not found. Save to outbox instead."}

    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_name = re.sub(r"[^a-z0-9-]", "-", filename.lower().replace(".yaml", ""))
    branch_name = f"guild/{artifact_type}/{safe_name}-{ts}"

    if artifact_type == "feedback":
        repo_path = f"feedback/{filename}"
    else:
        repo_path = f"packs/{filename}"

    provenance = artifact.get("provenance", {})
    confidence = provenance.get("confidence", "unknown")
    problem_class = artifact.get("problem_class", "N/A")
    phases = artifact.get("phases", [])
    phase_count = len(phases) if isinstance(phases, list) else 0

    if artifact_type == "feedback":
        pr_title = f"Feedback: {artifact.get('parent_artifact', 'unknown')}"
        pr_body = (
            f"## Guild Feedback Artifact\n\n"
            f"- **Parent artifact:** {artifact.get('parent_artifact', 'N/A')}\n"
            f"- **Confidence:** {confidence}\n"
            f"- **Execution log hash:** {artifact.get('execution_log_hash', 'N/A')}\n"
            f"- **What changed:** {artifact.get('what_changed', 'N/A')}\n"
            f"- **Where to reuse:** {artifact.get('where_to_reuse', 'N/A')}\n\n"
            f"Auto-generated by guild_publish. Review before merging."
        )
    else:
        pr_title = f"Pack: {artifact.get('id', filename)} ({confidence})"
        pr_body = (
            f"## Guild Workflow Pack\n\n"
            f"- **Artifact type:** {artifact_type}\n"
            f"- **Confidence:** {confidence}\n"
            f"- **Problem class:** {problem_class}\n"
            f"- **Phase count:** {phase_count}\n"
            f"- **Version:** {artifact.get('version', 'N/A')}\n"
            f"- **Evidence:** {provenance.get('evidence', 'N/A')}\n"
            f"- **Failure cases:** {provenance.get('failure_cases', [])}\n\n"
            f"Auto-generated by guild_publish. Review before merging."
        )

    target_repo = repo or DEFAULT_REPO

    try:
        tmp_dir = Path(f"/tmp/guild-publish-{ts}")
        tmp_dir.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["gh", "repo", "clone", target_repo, str(tmp_dir / "repo"), "--", "--depth=1"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"Clone failed: {result.stderr.strip()}"}

        repo_dir = tmp_dir / "repo"

        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            capture_output=True, text=True, cwd=repo_dir, timeout=30,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"Branch creation failed: {result.stderr.strip()}"}

        target_file = repo_dir / repo_path
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(artifact_yaml, encoding="utf-8")

        subprocess.run(["git", "add", repo_path], cwd=repo_dir, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "commit", "-m", f"guild: {artifact_type} — {filename}"],
            capture_output=True, text=True, cwd=repo_dir, timeout=30,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"Commit failed: {result.stderr.strip()}"}

        result = subprocess.run(
            ["git", "push", "origin", branch_name],
            capture_output=True, text=True, cwd=repo_dir, timeout=60,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"Push failed: {result.stderr.strip()}"}

        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--repo", target_repo,
                "--head", branch_name,
                "--base", DEFAULT_BRANCH,
                "--title", pr_title,
                "--body", pr_body,
            ],
            capture_output=True, text=True, cwd=repo_dir, timeout=60,
        )
        if result.returncode != 0:
            return {"success": False, "error": f"PR creation failed: {result.stderr.strip()}"}

        pr_url = result.stdout.strip()

        try:
            shutil.rmtree(tmp_dir)
        except Exception:
            pass

        return {"success": True, "pr_url": pr_url}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "GitHub operation timed out"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {e}"}


# ============================================================================
# Outbox save
# ============================================================================

def save_to_outbox(artifact: dict, artifact_yaml: str, filename: str) -> str:
    """Save artifact YAML to the local outbox directory.

    Returns the absolute path of the saved file.
    If the filename already exists, appends a timestamp to avoid overwrites.
    """
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    outbox_file = OUTBOX_DIR / filename
    if outbox_file.exists():
        ts = datetime.now(timezone.utc).strftime("%H%M%S")
        name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "yaml")
        outbox_file = OUTBOX_DIR / f"{name}-{ts}.{ext}"
    outbox_file.write_text(artifact_yaml, encoding="utf-8")
    return str(outbox_file)


# ============================================================================
# Action: list
# ============================================================================

def action_list() -> str:
    """List local artifacts (packs and feedback) available for publishing.

    Returns a JSON string with keys: success, artifacts (list), total (int).
    """
    artifacts: List[dict] = []

    if GUILD_DIR.exists():
        for pack_yaml in GUILD_DIR.glob("*/pack.yaml"):
            try:
                pack_data = yaml.safe_load(pack_yaml.read_text(encoding="utf-8"))
                if isinstance(pack_data, dict):
                    artifacts.append({
                        "type": "pack",
                        "name": pack_yaml.parent.name,
                        "path": str(pack_yaml),
                        "id": pack_data.get("id", pack_yaml.parent.name),
                        "confidence": pack_data.get("provenance", {}).get("confidence", "unknown"),
                    })
            except Exception:
                artifacts.append({
                    "type": "pack",
                    "name": pack_yaml.parent.name,
                    "path": str(pack_yaml),
                })

        if FEEDBACK_DIR.exists():
            for fb_yaml in FEEDBACK_DIR.glob("*.yaml"):
                try:
                    fb_data = yaml.safe_load(fb_yaml.read_text(encoding="utf-8"))
                    if isinstance(fb_data, dict):
                        artifacts.append({
                            "type": "feedback",
                            "name": fb_yaml.stem,
                            "path": str(fb_yaml),
                            "parent": fb_data.get("parent_artifact", "unknown"),
                        })
                except Exception:
                    artifacts.append({
                        "type": "feedback",
                        "name": fb_yaml.stem,
                        "path": str(fb_yaml),
                    })

    return json.dumps({
        "success": True,
        "artifacts": artifacts,
        "total": len(artifacts),
    })


# ============================================================================
# Action: publish
# ============================================================================

def action_publish(
    path: str = "",
    pack_name: str = "",
    feedback_name: str = "",
    repo: str = "",
) -> str:
    """Publish a pack or feedback artifact to the guild repo.

    Resolution order:
      1. Explicit path (any .yaml file under GUILD_DIR)
      2. pack_name -> GUILD_DIR/{pack_name}/pack.yaml
      3. feedback_name -> FEEDBACK_DIR/{feedback_name}*.yaml (most recent)

    Returns a JSON string with the result.
    """
    artifact_path: Optional[Path] = None

    if path:
        artifact_path = Path(path)
    elif pack_name:
        artifact_path = GUILD_DIR / pack_name / "pack.yaml"
    elif feedback_name:
        if FEEDBACK_DIR.exists():
            candidates = sorted(FEEDBACK_DIR.glob(f"{feedback_name}*.yaml"), reverse=True)
            if candidates:
                artifact_path = candidates[0]

    if not artifact_path or not artifact_path.exists():
        return json.dumps({
            "success": False,
            "error": f"Artifact not found. Looked for: path={path}, pack={pack_name}, feedback={feedback_name}",
            "hint": "Use guild_publish(action='list') to see available artifacts.",
        })

    # Security: restrict to files under GUILD_DIR only
    resolved = artifact_path.resolve()
    guild_resolved = GUILD_DIR.resolve()
    if not str(resolved).startswith(str(guild_resolved) + os.sep) and resolved != guild_resolved:
        return json.dumps({
            "success": False,
            "error": f"Path '{artifact_path}' is outside the guild directory. Only files under {GUILD_DIR} can be published.",
        })

    try:
        raw_yaml = artifact_path.read_text(encoding="utf-8")
        artifact = yaml.safe_load(raw_yaml)
    except Exception as e:
        return json.dumps({"success": False, "error": f"Failed to load artifact: {e}"})

    if not isinstance(artifact, dict):
        return json.dumps({"success": False, "error": "Artifact must be a YAML mapping"})

    artifact_type = artifact.get("type", "unknown")
    artifact_id = artifact.get("id", artifact_path.stem)

    # Rate limit check
    allowed, count_today = check_rate_limit()
    if not allowed:
        return json.dumps({
            "success": False,
            "error": f"Daily publish limit reached ({MAX_PUBLISHES_PER_DAY}/day). Already published {count_today} today.",
            "hint": "Try again tomorrow or adjust MAX_PUBLISHES_PER_DAY.",
        })

    # Proof gate validation (from sibling module)
    gate_errors = validate_proof_gates(artifact)
    if gate_errors:
        return json.dumps({
            "success": False,
            "error": "Proof gate validation failed",
            "gate_errors": gate_errors,
            "hint": "Fix these issues in the artifact before publishing.",
        })

    # Safety scan
    safety_threats = scan_pack_safety(artifact)
    if safety_threats:
        return json.dumps({
            "success": False,
            "error": "Safety scan failed",
            "threats": safety_threats,
        })

    # Privacy scan (sanitize before publishing)
    sanitized_artifact, privacy_findings = privacy_scan_artifact(artifact)
    if privacy_findings:
        logger.warning(
            "Privacy scan found %d issues, redacting before publish",
            len(privacy_findings),
        )

    sanitized_yaml = yaml.dump(sanitized_artifact, default_flow_style=False, sort_keys=False)

    safe_id = re.sub(r"[^a-zA-Z0-9_-]", "-", str(artifact_id).split("/")[-1])
    if artifact_type == "feedback":
        filename = f"{safe_id}.feedback.yaml"
    else:
        filename = f"{safe_id}.workflow.yaml"

    # Always save to outbox first (durable fallback)
    outbox_path = save_to_outbox(sanitized_artifact, sanitized_yaml, filename)

    # Attempt GitHub PR
    pr_result = create_github_pr(
        artifact=sanitized_artifact,
        artifact_yaml=sanitized_yaml,
        artifact_type=artifact_type,
        filename=filename,
        repo=repo,
    )

    if pr_result["success"]:
        log_publish(
            artifact_id=str(artifact_id),
            artifact_type=artifact_type,
            status="published",
            pr_url=pr_result["pr_url"],
        )

        # Log publish to reputation store (optional — store may not exist)
        if GuildStore is not None:
            try:
                _store = GuildStore()
                provenance = sanitized_artifact.get("provenance", {})
                _store.record_publish(
                    pack_id=str(artifact_id),
                    author_agent=provenance.get("author_agent", "unknown"),
                    confidence=provenance.get("confidence", "unknown"),
                    outcome="published",
                    metadata={"pr_url": pr_result["pr_url"], "artifact_type": artifact_type},
                )
                _store.close()
            except Exception:
                pass  # Store is optional — never break core flow

        return json.dumps({
            "success": True,
            "published": True,
            "pr_url": pr_result["pr_url"],
            "artifact_id": str(artifact_id),
            "outbox_path": outbox_path,
        })
    else:
        log_publish(
            artifact_id=str(artifact_id),
            artifact_type=artifact_type,
            status="outbox",
            outbox_path=outbox_path,
        )
        return json.dumps({
            "success": True,
            "published": False,
            "outbox_path": outbox_path,
            "error": pr_result.get("error", "Unknown error"),
            "hint": "Artifact saved to outbox. PR creation failed but can be retried manually.",
        })
