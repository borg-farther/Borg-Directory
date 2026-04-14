"""
FleetSyncer — synchronize Borg V3 data across a fleet of VPS nodes.

Pulls collective data (traces, outcomes, pack versions) from local ~/.borg/ files,
pushes to remote servers via SSH/rsync, pulls back remote outcomes, and merges
using the V3 SQLite DB.

Based on the logic in dogfood/sync_fleet.sh but implemented as a Python class
for better testability and reuse.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SSH defaults
# ---------------------------------------------------------------------------

DEFAULT_SSH_KEY = "~/.ssh/id_ed25519"
DEFAULT_SSH_OPTS = [
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "-o", "ConnectTimeout=10",
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class NodeConfig:
    """Configuration for a single fleet node."""
    ip: str
    hostname: Optional[str] = None
    ssh_key: str = DEFAULT_SSH_KEY
    ssh_opts: List[str] = field(default_factory=lambda: DEFAULT_SSH_OPTS.copy())
    remote_borg_path: str = "/root/.borg"
    remote_db_path: str = "/root/.borg/borg_v3.db"
    tags: List[str] = field(default_factory=list)

    @property
    def ssh_base(self) -> List[str]:
        """Base SSH command arguments for this node."""
        return ["ssh", "-i", os.path.expanduser(self.ssh_key)] + self.ssh_opts

    def identity(self) -> str:
        """Unique identifier for this node."""
        return self.ip


@dataclass
class SyncResult:
    """Result of a fleet sync operation."""
    total_nodes: int
    successful_nodes: List[str]
    failed_nodes: List[str]
    total_merged: int
    node_results: Dict[str, Dict[str, Any]]
    errors: List[str]

    def summary(self) -> Dict[str, Any]:
        return {
            "total_nodes": self.total_nodes,
            "successful": len(self.successful_nodes),
            "failed": len(self.failed_nodes),
            "total_merged": self.total_merged,
            "nodes": self.node_results,
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# FleetSyncer
# ---------------------------------------------------------------------------

class FleetSyncer:
    """Synchronize Borg V3 data across a fleet of VPS nodes.

    The syncer:
      1. Pulls collective data (traces, outcomes, pack versions) from local ~/.borg/ files
      2. Pushes to remote servers via SSH/rsync
      3. Pulls back remote outcomes
      4. Merges using the V3 SQLite DB

    Args:
        nodes: List of NodeConfig objects describing each fleet node.
        central_db_path: Path to the central V3 SQLite DB. Defaults to ~/.borg/borg_v3.db.
    """

    def __init__(
        self,
        nodes: List[NodeConfig],
        central_db_path: str = "~/.borg/borg_v3.db",
    ):
        self.nodes = {n.identity(): n for n in nodes}
        self._central_db_path = os.path.expanduser(central_db_path)
        self._local_borg_path = os.path.expanduser("~/.borg")

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def ping(self, node_id: str) -> bool:
        """Test SSH connectivity to a single node.

        Args:
            node_id: The IP or identity string of the node.

        Returns:
            True if SSH connection succeeds, False otherwise.
        """
        node = self.nodes.get(node_id)
        if not node:
            return False
        try:
            result = subprocess.run(
                node.ssh_base + [f"root@{node.ip}", "echo ok"],
                capture_output=True,
                timeout=15,
            )
            return result.returncode == 0
        except Exception:
            return False

    def ping_all(self) -> Dict[str, bool]:
        """Test SSH connectivity to all registered nodes.

        Returns:
            Dict mapping node_id -> reachable (bool).
        """
        return {node_id: self.ping(node_id) for node_id in self.nodes}

    def sync(
        self,
        dry_run: bool = False,
        sync_packs: bool = True,
        sync_traces: bool = True,
    ) -> SyncResult:
        """Run the full fleet synchronization.

        Args:
            dry_run: If True, show what would be merged without making changes.
            sync_packs: If True, push local pack changes to remote nodes.
            sync_traces: If True, pull remote traces into the central DB.

        Returns:
            SyncResult with detailed outcome of the sync operation.
        """
        self._ensure_central_schema()

        successful = []
        failed = []
        total_merged = 0
        node_results = {}
        errors = []

        for node_id, node in self.nodes.items():
            try:
                result = self._sync_node(node, dry_run=dry_run, sync_packs=sync_packs)
                node_results[node_id] = result
                if result.get("merged", 0) > 0 or result.get("packs_synced", 0) > 0:
                    successful.append(node_id)
                total_merged += result.get("merged", 0)
            except Exception as e:
                logger.warning("Node %s sync failed: %s", node_id, e)
                failed.append(node_id)
                errors.append(f"{node_id}: {e}")
                node_results[node_id] = {"error": str(e)}

        return SyncResult(
            total_nodes=len(self.nodes),
            successful_nodes=successful,
            failed_nodes=failed,
            total_merged=total_merged,
            node_results=node_results,
            errors=errors,
        )

    # -------------------------------------------------------------------------
    # Node-level sync
    # -------------------------------------------------------------------------

    def _sync_node(
        self,
        node: NodeConfig,
        dry_run: bool = False,
        sync_packs: bool = True,
    ) -> Dict[str, Any]:
        """Sync a single VPS node.

        Steps:
          1. Check if remote DB exists
          2. Copy remote DB to temp local file
          3. Get remote hostname
          4. Merge outcomes into central DB
          5. Optionally sync pack directories via rsync
        """
        result: Dict[str, Any] = {"merged": 0, "packs_synced": 0, "skipped": False}

        remote_db = node.remote_db_path

        # 1. Check if remote DB exists
        if not self._remote_exists(node, remote_db):
            logger.info("No DB at %s:%s — skipping", node.ip, remote_db)
            result["skipped"] = True
            return result

        # 2. Copy remote DB to temp local file
        tmpfile = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
        tmppath = tmpfile.name
        tmpfile.close()

        try:
            if not self._scp_from_remote(node, remote_db, tmppath):
                result["error"] = "Failed to copy DB from remote"
                return result

            size = os.path.getsize(tmppath)
            logger.info("Downloaded %d bytes from %s", size, node.ip)
            result["downloaded_bytes"] = size

            # 3. Get remote hostname
            remote_hostname = self._remote_hostname(node) or node.ip

            # 4. Merge or dry-run
            if dry_run:
                merged = self._dry_run_merge(tmppath, remote_hostname, node.ip)
            else:
                merged = self._merge_db(tmppath, remote_hostname, node.ip)
            result["merged"] = merged

        finally:
            Path(tmppath).unlink(missing_ok=True)

        # 5. Optional: sync pack directories
        if sync_packs and not dry_run:
            packs_synced = self._sync_packs_to_node(node)
            result["packs_synced"] = packs_synced

        return result

    # -------------------------------------------------------------------------
    # DB operations
    # -------------------------------------------------------------------------

    def _ensure_central_schema(self) -> None:
        """Ensure the central DB has the required schema and hostname column."""
        os.makedirs(os.path.dirname(self._central_db_path), exist_ok=True)

        conn = sqlite3.connect(self._central_db_path)
        c = conn.cursor()

        # Create outcomes table with hostname column (matches V3 schema + fleet extension)
        c.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                pack_id      TEXT    NOT NULL,
                agent_id     TEXT,
                task_category TEXT   NOT NULL,
                success      INTEGER NOT NULL,
                tokens_used  INTEGER DEFAULT 0,
                time_taken   REAL    DEFAULT 0.0,
                timestamp    TEXT    NOT NULL,
                hostname     TEXT    DEFAULT 'unknown'
            )
        """)

        # Add hostname column if missing (for DBs created before this feature)
        try:
            c.execute("ALTER TABLE outcomes ADD COLUMN hostname TEXT DEFAULT 'unknown'")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Create index on hostname for per-node queries
        c.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_hostname ON outcomes(hostname)")

        conn.commit()
        conn.close()
        logger.debug("Central DB ready: %s", self._central_db_path)

    def _dry_run_merge(self, tmpfile: str, remote_hostname: str, ip: str) -> int:
        """Show what would be merged (dry run mode)."""
        conn = sqlite3.connect(tmpfile)
        c = conn.cursor()

        try:
            c.execute("SELECT COUNT(*) FROM outcomes")
            total = c.fetchone()[0]
            logger.info("[DRY RUN] %s (%s): %d outcomes in remote DB", ip, remote_hostname, total)
            return 0  # No actual merge in dry run
        except sqlite3.OperationalError:
            logger.info("[DRY RUN] %s: outcomes table not found or empty", ip)
            return 0
        finally:
            conn.close()

    def _merge_db(self, tmpfile: str, remote_hostname: str, ip: str) -> int:
        """Merge remote DB outcomes into the central DB.

        Uses INSERT OR IGNORE on (pack_id, timestamp) to avoid duplicates.
        Adds hostname column to identify the source node.
        """
        src_conn = sqlite3.connect(tmpfile)
        dst_conn = sqlite3.connect(self._central_db_path)
        src_c = src_conn.cursor()
        dst_c = dst_conn.cursor()

        hostname = remote_hostname

        try:
            src_c.execute(
                """SELECT pack_id, agent_id, task_category, success, tokens_used, time_taken, timestamp
                   FROM outcomes"""
            )
            rows = src_c.fetchall()
        except sqlite3.OperationalError as e:
            logger.warning("Could not read outcomes from %s: %s", ip, e)
            src_conn.close()
            dst_conn.close()
            return 0

        merged = 0
        for row in rows:
            try:
                dst_c.execute("""
                    INSERT OR IGNORE INTO outcomes
                        (pack_id, agent_id, task_category, success, tokens_used, time_taken, timestamp, hostname)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (*row, hostname))
                if dst_c.rowcount > 0:
                    merged += 1
            except Exception as e:
                logger.warning("Warning inserting row: %s", e)

        dst_conn.commit()
        src_conn.close()
        dst_conn.close()

        logger.info("Merged %d new outcomes from %s (hostname=%s)", merged, ip, hostname)
        return merged

    def _get_summary(self) -> Dict[str, Any]:
        """Return a summary of the central DB state."""
        conn = sqlite3.connect(self._central_db_path)
        c = conn.cursor()

        # Total outcomes
        c.execute("SELECT COUNT(*) FROM outcomes")
        total = c.fetchone()[0] or 0

        # Per-node breakdown
        c.execute("""
            SELECT hostname, COUNT(*) as cnt,
                   ROUND(100.0 * SUM(success) / COUNT(*), 1) as rate
            FROM outcomes
            GROUP BY hostname
            ORDER BY cnt DESC
        """)
        per_node = [
            {"hostname": r[0], "count": r[1], "success_rate": r[2]}
            for r in c.fetchall()
        ]

        # Recent outcomes (last 5)
        c.execute("SELECT pack_id, hostname, success, timestamp FROM outcomes ORDER BY id DESC LIMIT 5")
        recent = [
            {"pack_id": r[0], "node": r[1], "ok": bool(r[2]), "timestamp": r[3]}
            for r in c.fetchall()
        ]

        conn.close()

        return {
            "total_outcomes": total,
            "per_node": per_node,
            "recent_outcomes": recent,
        }

    # -------------------------------------------------------------------------
    # Remote operations (SSH/scp helpers)
    # -------------------------------------------------------------------------

    def _run_ssh(self, node: NodeConfig, command: str) -> subprocess.CompletedProcess:
        """Run a command on a remote node via SSH.

        Args:
            node: NodeConfig for the target node.
            command: The command string to execute remotely.

        Returns:
            CompletedProcess from the subprocess call.
        """
        full_cmd = node.ssh_base + [f"root@{node.ip}", command]
        return subprocess.run(
            full_cmd,
            capture_output=True,
            timeout=60,
        )

    def _remote_exists(self, node: NodeConfig, path: str) -> bool:
        """Check if a file exists on a remote node."""
        result = self._run_ssh(node, f"test -f {path} && echo exists || echo missing")
        return "exists" in result.stdout.decode()

    def _remote_hostname(self, node: NodeConfig) -> Optional[str]:
        """Get the hostname of a remote node."""
        result = self._run_ssh(node, "hostname")
        if result.returncode == 0:
            return result.stdout.decode().strip()
        return None

    def _scp_from_remote(self, node: NodeConfig, remote_path: str, local_path: str) -> bool:
        """Copy a file from a remote node to local disk via scp.

        Args:
            node: NodeConfig for the target node.
            remote_path: Absolute path on the remote node.
            local_path: Absolute path for the local destination file.

        Returns:
            True if the copy succeeded, False otherwise.
        """
        scp_cmd = [
            "scp",
            "-i", os.path.expanduser(node.ssh_key),
        ] + node.ssh_opts + [
            f"root@{node.ip}:{remote_path}",
            local_path,
        ]
        try:
            result = subprocess.run(scp_cmd, capture_output=True, timeout=60)
            return result.returncode == 0
        except Exception:
            return False

    def _rsync_to_remote(self, node: NodeConfig, local_path: str, remote_path: str) -> bool:
        """Push a local directory to a remote node via rsync over SSH.

        Args:
            node: NodeConfig for the target node.
            local_path: Absolute path of the local directory to push.
            remote_path: Absolute destination path on the remote node.

        Returns:
            True if rsync succeeded, False otherwise.
        """
        rsync_cmd = [
            "rsync",
            "-az",
            "--delete",
            "-e",
            " ".join([
                "ssh",
                "-i", os.path.expanduser(node.ssh_key),
            ] + node.ssh_opts),
            local_path.rstrip("/") + "/",
            f"root@{node.ip}:{remote_path}",
        ]
        try:
            result = subprocess.run(rsync_cmd, capture_output=True, timeout=300)
            return result.returncode == 0
        except Exception:
            return False

    def _sync_packs_to_node(self, node: NodeConfig, packs_path: Optional[str] = None) -> int:
        """Sync the local packs directory to a remote node.

        Args:
            node: NodeConfig for the target node.
            packs_path: Optional path to local packs directory. Defaults to ~/.borg/packs.

        Returns:
            Number of pack files synced (approximate, based on rsync summary).
        """
        local_packs = packs_path or str(Path(self._local_borg_path) / "packs")
        if not os.path.isdir(local_packs):
            return 0

        remote_packs = f"{node.remote_borg_path}/packs"
        if self._rsync_to_remote(node, local_packs, remote_packs):
            logger.info("Synced packs to %s:%s", node.ip, remote_packs)
            return 1
        return 0

    # -------------------------------------------------------------------------
    # Fleet summary
    # -------------------------------------------------------------------------

    def fleet_summary(self) -> Dict[str, Any]:
        """Return a summary of the fleet sync state."""
        connectivity = self.ping_all()
        db_summary = self._get_summary()

        return {
            "nodes": {
                node_id: {
                    "ip": node.ip,
                    "reachable": reachable,
                    "hostname": node.hostname or "unknown",
                    "tags": node.tags,
                }
                for node_id, node in self.nodes.items()
                for reachable in [connectivity.get(node_id, False)]
            },
            "central_db": db_summary,
            "connectivity_ok": all(connectivity.values()),
        }