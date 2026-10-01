from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


# These are the only blocker families the PR watchdog may treat as an expected,
# fail-closed launch state. All other blockers remain CI failures. Governance,
# cold-start trust, and ops readiness are checked independently before this
# policy runs; this policy never converts a launch NO-GO into GO.
_ALLOWED_BLOCKER_MARKERS: dict[str, tuple[str, ...]] = {
    "first_10_evidence": (
        "first-10",
        "verified=",
        "external-user evidence",
        "protocol: protocol ",
    ),
    "package_provenance": (
        "pypi latest",
        "latest metadata",
        "pypi project description",
        "long-description",
        "package metadata",
        "package-impacting source/metadata",
        "immutable package reference",
        "fresh-install",
        "fresh install",
        "mcp stdio",
    ),
    "release_controls": (
        "served runtime",
        "version_matches_source",
        "reload_status",
        "release governance",
        "codeowners",
        "branch protection",
        "main branch is not protected",
    ),
}


def classify_blocker(blocker: str) -> str | None:
    normalized = blocker.strip().lower()
    for kind, markers in _ALLOWED_BLOCKER_MARKERS.items():
        if any(marker in normalized for marker in markers):
            return kind
    return None


def evaluate_expected_fail_closed_state(data: dict[str, Any]) -> dict[str, Any]:
    blockers = data.get("blockers")
    blocker_list = blockers if isinstance(blockers, list) else []
    typed_blockers = [blocker for blocker in blocker_list if isinstance(blocker, str)]
    classified = [
        {"blocker": blocker, "kind": classify_blocker(blocker)}
        for blocker in typed_blockers
    ]
    unknown = [row["blocker"] for row in classified if row["kind"] is None]

    public_ready = data.get("ready_for_public_self_serve_launch")
    controlled_ready = data.get("ready_for_controlled_first_10_beta")
    max_users = data.get("max_recommended_real_users_now")

    valid_rollout_shape = (
        (controlled_ready is True and max_users == 10)
        or (controlled_ready is False and max_users == 0)
    )
    violations: list[str] = []
    if public_ready is not False:
        violations.append("public self-serve must remain fail-closed")
    if not valid_rollout_shape:
        violations.append(
            "controlled-beta readiness and max user cap are inconsistent; "
            "expected (true, 10) or (false, 0)"
        )
    if len(typed_blockers) != len(blocker_list):
        violations.append("all blockers must be strings")
    if not typed_blockers:
        violations.append("fail-closed public state must name at least one blocker")
    if unknown:
        violations.append("unexpected blocker family present")

    return {
        "passed": not violations,
        "public_ready": public_ready,
        "controlled_ready": controlled_ready,
        "max_recommended_real_users_now": max_users,
        "classified_blockers": classified,
        "unknown_blockers": unknown,
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate that a public-launch NO-GO contains only expected fail-closed blocker families."
    )
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args(argv)

    data = json.loads(args.snapshot.read_text(encoding="utf-8"))
    result = evaluate_expected_fail_closed_state(data)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
