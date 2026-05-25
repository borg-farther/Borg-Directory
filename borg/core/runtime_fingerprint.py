"""Runtime fingerprint and canary helpers for Borg MCP.

This module is intentionally dependency-light and side-effect safe: it only
inspects loaded module paths, hashes source files, and evaluates the local
confidence-gate policy. It never restarts, signals, or mutates a running server.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import marshal
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


STALE_GUIDANCE_CANARY_TASK = """Continue production readiness review and implementation.

=== BORG GUIDANCE ===
CONFIDENCE: Real traces: 22 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
PACK GUIDANCE (bash-permission-denied)
1. Check file permissions
"""

STALE_PERMISSION_GUIDANCE = """CONFIDENCE: Real traces: 22 | Synthetic: 0 | BORG [HIGH CONFIDENCE]
PACK GUIDANCE (bash-permission-denied)
1. Check file permissions
2. chmod +x deploy.sh
"""

SYNTHETIC_PACK_GUIDANCE = """CONFIDENCE: Real traces: 0 | Synthetic: 0 | BORG [SYNTHETIC ONLY]
PACK GUIDANCE (bash-permission-denied)
1. chmod +x deploy.sh
"""

REAL_PERMISSION_TASK = "bash: ./deploy.sh: Permission denied"
META_TRUST_TASK = (
    "Audit product readiness and cold-start trust hardening. Explain why "
    "irrelevant Django/permission guidance leaked; do not debug Django."
)
META_TRUST_CONTEXT = "public self-service first-answer trust gate"
BANNED_META_TOKENS = ("pack guidance", "django", "migrate", "migration", "chmod", "permission denied", "apk", "apt-get", "npm")


def _source_version() -> Optional[str]:
    try:
        import tomllib  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - Python <3.11 fallback
        try:
            import tomli as tomllib  # type: ignore[no-redef]
        except Exception:
            return None
    try:
        root = Path(__file__).resolve().parents[2]
        pyproject = root / "pyproject.toml"
        if not pyproject.exists():
            return None
        return tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {}).get("version")
    except Exception:
        return None


def _function_code_hash(module_name: str, function_name: str) -> Dict[str, Any]:
    try:
        module = importlib.import_module(module_name)
        func = getattr(module, function_name)
        code = getattr(func, "__code__", None)
        if code is None:
            return {"exists": False, "sha256": None, "error": "no __code__"}
        payload = marshal.dumps(code)
        return {
            "exists": True,
            "module": module_name,
            "function": function_name,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "firstlineno": getattr(code, "co_firstlineno", None),
            "argcount": getattr(code, "co_argcount", None),
        }
    except Exception as exc:
        return {"exists": False, "module": module_name, "function": function_name, "sha256": None, "error": str(exc), "type": type(exc).__name__}


def _sha256_file(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            return None
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _file_info(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {"path": None, "exists": False, "sha256": None, "mtime": None, "size": None}
    try:
        p = Path(path)
        st = p.stat()
        return {
            "path": str(p),
            "exists": p.exists(),
            "sha256": _sha256_file(str(p)),
            "mtime": st.st_mtime,
            "mtime_iso_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(st.st_mtime)),
            "size": st.st_size,
        }
    except OSError:
        return {"path": str(path), "exists": False, "sha256": None, "mtime": None, "size": None}


def _module_file(module_name: str) -> Optional[str]:
    try:
        module = importlib.import_module(module_name)
        return getattr(module, "__file__", None)
    except Exception:
        return None


def _confidence_gate_canary() -> Dict[str, Any]:
    try:
        from borg.core.confidence_gate import (
            guidance_is_safe_to_inject,
            permission_guidance_matches_task,
            strip_embedded_borg_guidance,
        )

        cleaned = strip_embedded_borg_guidance(STALE_GUIDANCE_CANARY_TASK)
        stale_permission_match = permission_guidance_matches_task(STALE_GUIDANCE_CANARY_TASK, "")
        stale_permission_safe = guidance_is_safe_to_inject(
            STALE_PERMISSION_GUIDANCE,
            STALE_GUIDANCE_CANARY_TASK,
            "operator meta instruction",
        )
        synthetic_safe = guidance_is_safe_to_inject(
            SYNTHETIC_PACK_GUIDANCE,
            "continue production readiness implementation",
            "operator meta instruction",
        )
        real_permission_safe = guidance_is_safe_to_inject(
            STALE_PERMISSION_GUIDANCE,
            REAL_PERMISSION_TASK,
            REAL_PERMISSION_TASK,
        )
        passed = (
            "PACK GUIDANCE" not in cleaned
            and stale_permission_match is False
            and stale_permission_safe is False
            and synthetic_safe is False
            and real_permission_safe is True
        )
        return {
            "passed": passed,
            "stale_guidance_stripped": "PACK GUIDANCE" not in cleaned,
            "stale_permission_match": stale_permission_match,
            "stale_permission_safe": stale_permission_safe,
            "synthetic_pack_safe": synthetic_safe,
            "real_permission_positive_control_safe": real_permission_safe,
        }
    except Exception as exc:
        return {"passed": False, "error": str(exc), "type": type(exc).__name__}


def _observe_behavior_canary() -> Dict[str, Any]:
    """Probe loaded observe policy without calling full retrieval.

    `borg_runtime_fingerprint` must be side-effect safe: no seeding, no trace
    recording, no retrieval, and no network/embedder path.  This canary checks
    the loaded MCP module's final injection boundary and technology detection
    helpers with synthetic strings. A separate stdio subprocess canary proves
    full `borg_observe` behavior before release.
    """
    try:
        from borg.integrations import mcp_server

        meta_task = "Audit why previous Borg answer said chmod +x; do not debug permissions."
        stale_permission_safe = mcp_server._guidance_is_safe_to_inject(
            STALE_PERMISSION_GUIDANCE,
            meta_task,
            "operator meta instruction",
        )
        meta_tech = mcp_server._detect_technology(META_TRUST_TASK, META_TRUST_CONTEXT)
        concrete_permission_safe = mcp_server._guidance_is_safe_to_inject(
            STALE_PERMISSION_GUIDANCE,
            REAL_PERMISSION_TASK,
            REAL_PERMISSION_TASK,
        )
        synthetic_permission_safe = mcp_server._guidance_is_safe_to_inject(
            SYNTHETIC_PACK_GUIDANCE,
            "continue production readiness implementation",
            "operator meta instruction",
        )
        blockers = []
        if stale_permission_safe:
            blockers.append("meta prior-answer prompt allowed permission guidance injection")
        if meta_tech in {"django", "bash", "nodejs"}:
            blockers.append(f"meta trust prompt was misclassified as concrete tech: {meta_tech}")
        if not concrete_permission_safe:
            blockers.append("concrete permission prompt did not allow permission guidance")
        if synthetic_permission_safe:
            blockers.append("synthetic permission guidance was injectable for meta readiness prompt")
        meta_failed_closed = not stale_permission_safe and meta_tech not in {"django", "bash", "nodejs"}
        return {
            "passed": not blockers,
            "blockers": blockers,
            "side_effect_safe": True,
            "meta_prior_answer_permission_guidance_safe": stale_permission_safe,
            "meta_detected_technology": meta_tech,
            "permission_prompt_specific": concrete_permission_safe,
            "synthetic_meta_guidance_safe": synthetic_permission_safe,
            # Backward-compatible field names for older canary consumers. These
            # are derived from helper-level policy checks, not full retrieval.
            "meta_prompt_failed_closed": meta_failed_closed,
            "meta_excerpt": "NO_CONFIDENT_MATCH (side-effect-safe helper canary; full stdio canary lives in eval/cold_start_trust_gate.py)",
            "permission_excerpt": "ACTION: concrete Permission denied prompt is eligible for permission-specific guidance.",
        }
    except Exception as exc:
        return {"passed": False, "error": str(exc), "type": type(exc).__name__}


def runtime_fingerprint() -> Dict[str, Any]:
    """Return a machine-readable fingerprint of the loaded Borg runtime."""
    borg_file = _module_file("borg")
    mcp_file = _module_file("borg.integrations.mcp_server")
    confidence_file = _module_file("borg.core.confidence_gate")
    runtime_file = _module_file("borg.core.runtime_fingerprint")

    try:
        import borg
        borg_version = getattr(borg, "__version__", None)
    except Exception:
        borg_version = None

    canary = _confidence_gate_canary()
    observe_canary = _observe_behavior_canary()
    source_version = _source_version()
    try:
        from borg.core.dirs import get_paths_summary
        paths = get_paths_summary()
    except Exception as exc:
        paths = {"error": str(exc), "type": type(exc).__name__}
    return {
        "success": True,
        "tool": "borg_runtime_fingerprint",
        "schema_version": 1,
        "pid": os.getpid(),
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "cwd": os.getcwd(),
        "borg_home": paths.get("borg_home"),
        "borg_dir": paths.get("borg_dir"),
        "paths": paths,
        "borg_version": borg_version,
        "source_version": source_version,
        "version_matches_source": bool(source_version and borg_version == source_version),
        "modules": {
            "borg": _file_info(borg_file),
            "borg.integrations.mcp_server": _file_info(mcp_file),
            "borg.core.confidence_gate": _file_info(confidence_file),
            "borg.core.runtime_fingerprint": _file_info(runtime_file),
        },
        "sys_path_head": sys.path[:8],
        "loaded_function_hashes": {
            "borg.integrations.mcp_server.borg_observe": _function_code_hash("borg.integrations.mcp_server", "borg_observe"),
            "borg.integrations.mcp_server._detect_technology": _function_code_hash("borg.integrations.mcp_server", "_detect_technology"),
            "borg.core.confidence_gate.trace_match_is_confident": _function_code_hash("borg.core.confidence_gate", "trace_match_is_confident"),
        },
        "confidence_gate_canary": canary,
        "observe_behavior_canary": observe_canary,
        "reload_status": "loaded_code_matches_source_behavior" if canary.get("passed") and observe_canary.get("passed") and bool(source_version and borg_version == source_version) else "reload_or_patch_required",
    }


def runtime_fingerprint_json(indent: Optional[int] = None) -> str:
    return json.dumps(runtime_fingerprint(), ensure_ascii=False, sort_keys=True, indent=indent)
