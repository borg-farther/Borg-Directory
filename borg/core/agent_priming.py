"""Host-specific Borg priming candidates and safe local install manifests.

The optimizer target here is not pack content; it is the tiny rule block that
makes agents call Borg at the right time and close the outcome loop. Installs
are deliberately local, manifest-backed, reversible, and block-scoped so Borg
never clobbers user-authored rule files.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
from typing import Any

_HOST_LABELS = {
    "claude-code": "Claude Code",
    "codex": "Codex CLI",
    "cursor": "Cursor",
    "hermes": "Hermes Agent",
    "generic": "generic agent",
}
_REQUIRED_TERMS = ("borg_observe", "error_lookup", "NO_CONFIDENT_MATCH", "borg_record_outcome", "VERIFY")
_FLAG_OVERCLAIM_RE = re.compile(r"(?i)([\"']?(first[_-]?10[_-]?claim|global[_-]?promotion[_-]?allowed|public[_-]?lift[_-]?claim)[\"']?\s*[:=]\s*(true|yes|1))")
_NATURAL_OVERCLAIM_RE = re.compile(r"(?i)(borg\s+(has\s+)?(proven|verified|achieved)\s+first[-_\s]?10\s+lift|public\s+lift\s+(is\s+)?(proven|verified|achieved)|global\s+promotion\s+(is\s+)?(approved|allowed|ready))")
_UNSAFE_TRUST_RE = re.compile(r"(?i)(always\s+trust\s+borg|skip\s+verify|do\s+not\s+verify|ignore\s+verification)")
_MANAGED_BLOCK_RE = re.compile(
    r"<!-- BEGIN BORG AGENT PRIMING host=(?P<host>[a-z0-9-]+) install_id=(?P<install_id>[a-f0-9]{16,64}) prompt_sha256=(?P<prompt_sha256>sha256:[a-f0-9]{64}) -->\n"
    r"(?P<body>.*?)"
    r"<!-- END BORG AGENT PRIMING -->\n?",
    re.DOTALL,
)


def _sha256_ref(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def _normalize_host(host: str) -> str:
    value = str(host or "generic").strip().lower().replace("_", "-")
    return value if value in _HOST_LABELS else "generic"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fallback_state(code: str, message: str, *, severity: str = "info", next_step: str = "") -> dict[str, str]:
    state = {"code": code, "severity": severity, "message": message}
    if next_step:
        state["next"] = next_step
    return state


def _default_manifest_path(host: str) -> Path:
    from borg.core.dirs import get_borg_home

    return get_borg_home() / "agent-priming" / _normalize_host(host) / "manifest.json"


def _default_target_path(host: str) -> Path:
    from borg.core.dirs import get_borg_home

    return get_borg_home() / "agent-priming" / _normalize_host(host) / "BORG_AGENT_PRIMING.md"


def _hmac_key_path() -> Path:
    from borg.core.dirs import get_borg_home

    return get_borg_home() / "agent-priming" / ".manifest-hmac-key"


def _as_path(value: str | os.PathLike[str] | None, *, default: Path) -> Path:
    if value is None or str(value).strip() == "":
        path = default.expanduser()
    else:
        if "\x00" in str(value):
            raise ValueError("path contains NUL byte")
        path = Path(value).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    # abspath normalizes relative components without resolving symlinks. We
    # separately reject existing symlink path components before writes/unlinks.
    return Path(os.path.abspath(os.fspath(path)))


def _reject_existing_symlinks(path: Path, label: str) -> None:
    """Reject a path if it or any existing parent is a symlink.

    This is stricter than resolving then writing: it prevents a user-controlled
    symlink from redirecting Borg-managed blocks into arbitrary files.
    """
    path = Path(path)
    candidates = [path] + list(path.parents)
    for candidate in candidates:
        try:
            if candidate.is_symlink():
                raise ValueError(f"refusing {label} symlink path: {candidate}")
        except OSError as e:
            raise ValueError(f"cannot inspect {label} path {candidate}: {e}") from e


def _atomic_write(path: Path, content: str) -> None:
    _reject_existing_symlinks(path, "write target")
    path.parent.mkdir(parents=True, exist_ok=True)
    _reject_existing_symlinks(path.parent, "write parent")
    fd = None
    tmp_name = ""
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        _reject_existing_symlinks(path, "write target")
        os.replace(tmp_name, path)
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_name:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass


def _load_hmac_key(*, create: bool) -> bytes:
    key_path = _hmac_key_path()
    _reject_existing_symlinks(key_path, "manifest hmac key")
    if key_path.exists():
        value = key_path.read_text(encoding="utf-8").strip()
        if not re.fullmatch(r"[a-f0-9]{64}", value):
            raise ValueError("manifest hmac key is invalid")
        return bytes.fromhex(value)
    if not create:
        raise ValueError("manifest hmac key missing")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    _reject_existing_symlinks(key_path.parent, "manifest hmac key parent")
    key = secrets.token_bytes(32)
    fd = None
    tmp_name = ""
    try:
        fd, tmp_name = tempfile.mkstemp(prefix=f".{key_path.name}.", suffix=".tmp", dir=str(key_path.parent))
        os.chmod(tmp_name, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            handle.write(key.hex() + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, key_path)
    finally:
        if fd is not None:
            os.close(fd)
        if tmp_name:
            try:
                Path(tmp_name).unlink(missing_ok=True)
            except OSError:
                pass
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def _canonical_manifest_payload(payload: dict[str, Any]) -> str:
    filtered = {k: v for k, v in payload.items() if k != "manifest_hmac_sha256"}
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _manifest_hmac(payload: dict[str, Any], key: bytes) -> str:
    return "sha256:" + hmac.new(key, _canonical_manifest_payload(payload).encode("utf-8"), hashlib.sha256).hexdigest()


def _attach_manifest_hmac(payload: dict[str, Any]) -> dict[str, Any]:
    keyed = dict(payload)
    keyed["manifest_hmac_sha256"] = None
    keyed["manifest_hmac_sha256"] = _manifest_hmac(keyed, _load_hmac_key(create=True))
    return keyed


def _verify_manifest_hmac(payload: dict[str, Any]) -> None:
    actual = payload.get("manifest_hmac_sha256")
    if not isinstance(actual, str) or not actual.startswith("sha256:"):
        raise ValueError("manifest hmac missing or invalid")
    expected = _manifest_hmac(payload, _load_hmac_key(create=False))
    if not hmac.compare_digest(actual, expected):
        raise ValueError("manifest hmac mismatch")


def _install_id(host: str, target: Path, prompt: str) -> str:
    material = f"{_normalize_host(host)}\n{target}\n{_sha256_ref(prompt)}"
    return hashlib.sha256(material.encode("utf-8", "ignore")).hexdigest()[:16]


def _render_managed_block(host: str, prompt: str, *, install_id: str) -> str:
    normalized = _normalize_host(host)
    prompt_text = str(prompt or "").rstrip() + "\n"
    prompt_sha = _sha256_ref(prompt_text)
    return (
        f"<!-- BEGIN BORG AGENT PRIMING host={normalized} install_id={install_id} prompt_sha256={prompt_sha} -->\n"
        f"{prompt_text}"
        "<!-- END BORG AGENT PRIMING -->\n"
    )


def _find_host_block(content: str, host: str) -> re.Match[str] | None:
    normalized = _normalize_host(host)
    matches = [m for m in _MANAGED_BLOCK_RE.finditer(content or "") if m.group("host") == normalized]
    if len(matches) > 1:
        raise ValueError(f"multiple Borg managed priming blocks found for host {normalized}")
    return matches[0] if matches else None


def _assert_no_malformed_managed_markers(content: str) -> None:
    """Fail closed when Borg-looking markers are present but not a valid block.

    A malformed marker can otherwise be treated as user text during install and
    survive a later uninstall as stale agent instructions.
    """
    text = content or ""
    if "BORG AGENT PRIMING" not in text:
        return
    valid_spans = [range(m.start(), m.end()) for m in _MANAGED_BLOCK_RE.finditer(text)]
    for marker in re.finditer(r"BORG AGENT PRIMING", text):
        if not any(marker.start() in span for span in valid_spans):
            raise ValueError("malformed Borg managed priming marker; remove or repair manually before install/uninstall")


def _validate_existing_manifest_for_install(
    manifest: Path,
    *,
    host: str,
    target_file: Path,
    install_id: str,
    block: str,
) -> None:
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0" or data.get("kind") != "borg_agent_priming_install_manifest":
        raise ValueError("invalid agent priming manifest")
    _verify_manifest_hmac(data)
    if _normalize_host(str(data.get("host") or "")) != _normalize_host(host):
        raise ValueError("manifest host mismatch")
    if _as_path(data.get("manifest_path"), default=manifest) != manifest:
        raise ValueError("manifest path mismatch")
    if _as_path(data.get("target_file"), default=target_file) != target_file:
        raise ValueError("manifest target mismatch")
    if data.get("install_id") != install_id:
        raise ValueError("manifest install_id mismatch")
    if data.get("managed_block_sha256") != _sha256_ref(block):
        raise ValueError("manifest managed block hash mismatch")


def _merge_managed_block(existing: str, host: str, block: str) -> tuple[str, bool, str]:
    _assert_no_malformed_managed_markers(existing)
    match = _find_host_block(existing, host)
    if match:
        current = match.group(0)
        if current == block:
            return existing, False, "already_installed"
        return existing[: match.start()] + block + existing[match.end() :], True, "updated_managed_block"
    separator = "" if not existing or existing.endswith("\n") else "\n"
    return existing + separator + block, True, "appended_managed_block"


def _manifest_payload(
    *,
    host: str,
    target_file: Path,
    manifest_path: Path,
    prompt: str,
    block: str,
    install_id: str,
    created_file: bool,
    previous_text: str,
    installed_text: str,
) -> dict[str, Any]:
    candidate = build_agent_priming_candidate(host)
    return {
        "schema_version": "1.0",
        "kind": "borg_agent_priming_install_manifest",
        "managed_by": "borg",
        "mode": "managed_block",
        "host": _normalize_host(host),
        "host_label": candidate["host_label"],
        "install_id": install_id,
        "target_file": str(target_file),
        "manifest_path": str(manifest_path),
        "created_file": bool(created_file),
        "installed_at": _utc_now(),
        "prompt_sha256": _sha256_ref(str(prompt or "").rstrip() + "\n"),
        "managed_block_sha256": _sha256_ref(block),
        "previous_file_sha256": _sha256_ref(previous_text) if previous_text else None,
        "installed_file_sha256": _sha256_ref(installed_text),
        "call_rules": candidate["call_rules"],
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
        "manifest_hmac_sha256": None,
    }


def score_agent_priming(prompt: str) -> dict[str, Any]:
    """Score whether a priming block teaches the right Borg interaction loop."""
    text = str(prompt or "")
    lowered = text.lower()
    missing = [term for term in _REQUIRED_TERMS if term.lower() not in lowered]
    hard_failures: list[str] = []
    if _FLAG_OVERCLAIM_RE.search(text) or _NATURAL_OVERCLAIM_RE.search(text):
        hard_failures.append("overclaim")
    if _UNSAFE_TRUST_RE.search(text):
        hard_failures.append("unsafe_trust_instruction")
    if missing:
        hard_failures.append("missing_required_call_rules")
    score = 0.0 if hard_failures else 1.0
    return {
        "schema_version": "1.0",
        "score": score,
        "required_terms_present": sorted(set(_REQUIRED_TERMS) - set(missing)),
        "missing_terms": missing,
        "hard_failures": hard_failures,
    }


def build_agent_priming_candidate(host: str = "generic") -> dict[str, Any]:
    """Return a host-specific priming artifact for maintainer review/export."""
    normalized = _normalize_host(host)
    label = _HOST_LABELS[normalized]
    prompt = (
        f"Borg interaction rule for {label}:\n"
        "- At the start of technical debug/test/review/deploy work, call `borg_observe` once with the exact task and tech context.\n"
        "- When there is a concrete error, failing command, stack trace, or repeated failure, call `error_lookup` / `borg_rescue` with the exact text before changing code.\n"
        "- If Borg returns `NO_CONFIDENT_MATCH`, say that plainly; do not blend weak retrieval into the answer or pretend Borg helped.\n"
        "- Follow Borg's `ACTION`, avoid `STOP`, then rerun the exact `VERIFY` command/test.\n"
        "- after VERIFY, call `borg_record_outcome` with the intervention_id, outcome, helpful, verified, and verification evidence so Borg learns.\n"
        "- Surface fallback states by exact code instead of hiding degraded mode: `OUTCOME_NOT_RECORDED`, `SEMANTIC_SEARCH_LEXICAL_FALLBACK`, `MCP_UNAVAILABLE_USE_CLI`, and `LOCAL_SEED_NOT_COLLECTIVE_PROOF`.\n"
        "- Borg guidance is advisory until verified; never claim first-10 lift, public lift, or global promotion from this local priming block.\n"
    )
    score = score_agent_priming(prompt)
    artifact = {
        "schema_version": "1.0",
        "host": normalized,
        "host_label": label,
        "prompt": prompt,
        "prompt_sha256": _sha256_ref(prompt),
        "call_rules": {
            "task_start_debug_test_review": "borg_observe",
            "concrete_error": "error_lookup",
            "weak_match": "NO_CONFIDENT_MATCH",
            "after_verify": "borg_record_outcome",
        },
        "visible_fallback_contract": {
            "NO_CONFIDENT_MATCH": "say NO_CONFIDENT_MATCH plainly; proceed without attributing the fix to Borg",
            "OUTCOME_NOT_RECORDED": "rerun VERIFY, then call borg_record_outcome",
            "SEMANTIC_SEARCH_LEXICAL_FALLBACK": "tell the user search fell back to lexical/text matching",
            "MCP_UNAVAILABLE_USE_CLI": "use the Borg CLI fallback: borg rescue '<exact failure>'",
            "LOCAL_SEED_NOT_COLLECTIVE_PROOF": "state that the result came from bundled local seed knowledge, not collective proof",
        },
        "score": score,
        "first_10_claim": False,
        "global_promotion_allowed": False,
        "public_lift_claim": False,
    }
    # Make accidental future edits fail closed if they weaken the loop.
    if score["hard_failures"]:
        artifact["recommendation"] = "blocked"
    else:
        artifact["recommendation"] = "eligible_for_host_rules_review"
    return artifact


def install_agent_priming(
    host: str = "generic",
    *,
    target_file: str | os.PathLike[str] | None = None,
    manifest_path: str | os.PathLike[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Install a Borg priming block into a local rules file.

    The write is manifest-backed and block-scoped. Existing user text is
    preserved; only the Borg managed block is appended/replaced. Symlink targets
    and symlink manifests are refused.
    """
    normalized = _normalize_host(host)
    target = _as_path(target_file, default=_default_target_path(normalized))
    manifest = _as_path(manifest_path, default=_default_manifest_path(normalized))
    if target == manifest:
        raise ValueError("manifest path must differ from target file")
    _reject_existing_symlinks(target, "target")
    _reject_existing_symlinks(manifest, "manifest")

    candidate = build_agent_priming_candidate(normalized)
    if candidate.get("recommendation") != "eligible_for_host_rules_review":
        raise ValueError(f"agent priming candidate is blocked: {candidate.get('score', {}).get('hard_failures', [])}")
    prompt = candidate["prompt"]
    install_id = _install_id(normalized, target, prompt)
    block = _render_managed_block(normalized, prompt, install_id=install_id)
    previous_text = target.read_text(encoding="utf-8") if target.exists() else ""
    created_file = not target.exists()
    installed_text, changed, status = _merge_managed_block(previous_text, normalized, block)
    manifest_payload = _manifest_payload(
        host=normalized,
        target_file=target,
        manifest_path=manifest,
        prompt=prompt,
        block=block,
        install_id=install_id,
        created_file=created_file,
        previous_text=previous_text,
        installed_text=installed_text,
    )
    states = [
        _fallback_state(
            "LOCAL_ONLY_INSTALL",
            "Agent priming install is local and does not publish, pull, or globally promote Borg rules.",
            next_step="review the managed block before relying on it in an agent host",
        )
    ]
    if dry_run:
        states.insert(0, _fallback_state("DRY_RUN_NO_WRITE", "Dry run only; target and manifest were not written."))
    if previous_text and changed:
        states.append(_fallback_state("USER_CONTENT_PRESERVED", "Existing user-authored file text is preserved; Borg edits only its managed block."))

    validated_existing_manifest = False
    key_path = _hmac_key_path()
    hmac_key_preexisted = key_path.exists()
    hmac_key_may_have_been_created = False
    if not dry_run and not changed and manifest.exists():
        _validate_existing_manifest_for_install(
            manifest,
            host=normalized,
            target_file=target,
            install_id=install_id,
            block=block,
        )
        manifest_payload = json.loads(manifest.read_text(encoding="utf-8"))
        validated_existing_manifest = True
    elif not dry_run:
        manifest_payload = _attach_manifest_hmac(manifest_payload)
        hmac_key_may_have_been_created = not hmac_key_preexisted

    result = {
        "success": True,
        "schema_version": "1.0",
        "operation": "install",
        "status": status,
        "host": normalized,
        "dry_run": bool(dry_run),
        "changed": bool(changed),
        "created_file": bool(created_file),
        "target_file": str(target),
        "manifest_path": str(manifest),
        "managed_block_sha256": _sha256_ref(block),
        "prompt_sha256": manifest_payload["prompt_sha256"],
        "fallback_states": states,
        "manifest": manifest_payload,
    }
    if dry_run:
        return result

    if validated_existing_manifest:
        return result

    wrote_target = False
    try:
        if changed:
            _atomic_write(target, installed_text)
            wrote_target = True
        if changed or not manifest.exists():
            _atomic_write(manifest, json.dumps(manifest_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    except Exception:
        if wrote_target:
            try:
                if created_file:
                    target.unlink(missing_ok=True)
                else:
                    _atomic_write(target, previous_text)
            except Exception:
                pass
        if hmac_key_may_have_been_created and not hmac_key_preexisted:
            try:
                key_path.unlink(missing_ok=True)
            except Exception:
                pass
            try:
                key_path.parent.rmdir()
            except OSError:
                pass
        raise
    return result


def uninstall_agent_priming(
    host: str = "generic",
    *,
    manifest_path: str | os.PathLike[str] | None = None,
    target_file: str | os.PathLike[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Remove only the Borg managed priming block described by the manifest."""
    normalized = _normalize_host(host)
    manifest = _as_path(manifest_path, default=_default_manifest_path(normalized))
    _reject_existing_symlinks(manifest, "manifest")
    if not manifest.exists():
        raise FileNotFoundError(f"agent priming manifest not found: {manifest}")
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0" or data.get("kind") != "borg_agent_priming_install_manifest":
        raise ValueError("invalid agent priming manifest")
    _verify_manifest_hmac(data)
    if _normalize_host(str(data.get("host") or "")) != normalized:
        raise ValueError("agent priming manifest host mismatch")
    if _as_path(data.get("manifest_path"), default=manifest) != manifest:
        raise ValueError("agent priming manifest path mismatch")
    target = _as_path(data.get("target_file"), default=_default_target_path(normalized))
    if target_file is not None:
        expected_target = _as_path(target_file, default=target)
        if expected_target != target:
            raise ValueError("target file mismatch: manifest points at a different file")
    if target == manifest:
        raise ValueError("manifest path must differ from target file")
    _reject_existing_symlinks(target, "target")
    previous_text = target.read_text(encoding="utf-8") if target.exists() else ""
    _assert_no_malformed_managed_markers(previous_text)
    match = _find_host_block(previous_text, normalized)
    if not match:
        if target.exists():
            raise ValueError("managed block not found; refusing to remove manifest for a possibly tampered target")
        changed = False
        status = "already_uninstalled"
        new_text = previous_text
    else:
        block = match.group(0)
        if match.group("install_id") != data.get("install_id"):
            raise ValueError("managed block install_id mismatch; refusing to remove a tampered block")
        if _sha256_ref(block) != data.get("managed_block_sha256"):
            raise ValueError("managed block hash mismatch; refusing to remove a tampered block")
        new_text = previous_text[: match.start()] + previous_text[match.end() :]
        changed = True
        status = "removed_managed_block"
    remove_target_file = bool(data.get("created_file") and not new_text.strip())
    states = [
        _fallback_state(
            "MANIFEST_BACKED_UNINSTALL",
            "Uninstall removes only the Borg managed block recorded in the manifest.",
        )
    ]
    if dry_run:
        states.insert(0, _fallback_state("DRY_RUN_NO_WRITE", "Dry run only; target and manifest were not modified."))

    result = {
        "success": True,
        "schema_version": "1.0",
        "operation": "uninstall",
        "status": status,
        "host": normalized,
        "dry_run": bool(dry_run),
        "changed": bool(changed),
        "removed_target_file": bool(remove_target_file),
        "target_file": str(target),
        "manifest_path": str(manifest),
        "fallback_states": states,
    }
    if dry_run:
        return result

    target_existed_before = target.exists()
    target_mutated = False
    try:
        if changed:
            if remove_target_file:
                target.unlink(missing_ok=True)
            else:
                _atomic_write(target, new_text)
            target_mutated = True
        manifest.unlink(missing_ok=True)
    except Exception:
        if target_mutated:
            try:
                if target_existed_before:
                    _atomic_write(target, previous_text)
                else:
                    target.unlink(missing_ok=True)
            except Exception:
                pass
        raise
    try:
        manifest.parent.rmdir()
    except OSError:
        pass
    return result


def render_agent_priming(host: str = "generic") -> str:
    return build_agent_priming_candidate(host)["prompt"]


def dumps_agent_priming(host: str = "generic") -> str:
    return json.dumps(build_agent_priming_candidate(host), indent=2, sort_keys=True, ensure_ascii=False)
